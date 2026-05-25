import os
import time
import logging
from typing import Dict, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
import requests
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.backends import default_backend

# Setup Logging
logger = logging.getLogger("mcp_auth")
logging.basicConfig(level=logging.INFO)

security = HTTPBearer()

class AzureADTokenVerifier:
    """
    Decodes and validates JWT Access Tokens from Microsoft Entra ID (Azure AD).
    Implements a thread-safe cache for JSON Web Key Sets (JWKS) to avoid calling Microsoft endpoints on every request.
    """
    def __init__(self):
        self.tenant_id = os.getenv("AZURE_TENANT_ID", "common")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.verify_issuer = os.getenv("AZURE_VERIFY_ISSUER", "true").lower() == "true"
        self.required_scope = os.getenv("AZURE_REQUIRED_SCOPE", "mcp.read")

        # Cache variables for JWKS
        self.jwks_url = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        self.jwks_cache: Dict = {}
        self.jwks_last_fetched: float = 0.0
        self.jwks_ttl: int = 86400  # Sync keys once every 24 hours

        # Expected Issuers based on tenant
        if self.tenant_id == "common":
            self.expected_issuers = [
                "https://login.microsoftonline.com/common/v2.0",
                "https://sts.windows.net/common/"
            ]
        else:
            self.expected_issuers = [
                f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
                f"https://sts.windows.net/{self.tenant_id}/"
            ]

    def _fetch_jwks(self) -> Dict:
        """Fetch JWKS keys and cache them."""
        now = time.time()
        if not self.jwks_cache or (now - self.jwks_last_fetched) > self.jwks_ttl:
            try:
                logger.info(f"Fetching Azure AD Microsoft JWKS from {self.jwks_url}")
                response = requests.get(self.jwks_url, timeout=5)
                response.raise_for_status()
                self.jwks_cache = response.json()
                self.jwks_last_fetched = now
            except Exception as e:
                logger.error(f"Failed to fetch Microsoft JWKS: {str(e)}")
                if self.jwks_cache:
                    logger.warning("Falling back to stale cached JWKS")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Failed to fetch authorization signing keys from identity provider"
                    )
        return self.jwks_cache

    def get_public_key(self, kid: str) -> RSAPublicKey:
        """Finds the public key in JWKS keys list that matches the token identifier (kid)."""
        jwks = self._fetch_jwks()
        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                # Convert JWKS RSA parameters to pyjwt-friendly public certificate/key
                # JWKS gives 'n' and 'e' parameter modulus and exponent
                try:
                    from jwt.algorithms import RSAAlgorithm
                    return RSAAlgorithm.from_jwk(key_data)
                except Exception as e:
                    logger.error(f"Error parsing asymmetric public key for client validation: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Cryptographic key loading failure"
                    )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header key identifier 'kid' not recognized in registry"
        )

    def verify_token(self, token: str) -> Dict:
        """
        Validates the signature, expiration, client audience, and required scope.
        Returns the decoded payload if valid.
        """
        if not self.client_id:
            logger.warning("AZURE_CLIENT_ID environment variable is missing. Audience check will fail.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security configuration error: client audience is undefined"
            )

        try:
            # First pass decode: Extract unverified header to get key identifier 'kid'
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token header. Missing 'kid'."
                )

            # Retrieve actual asymmetric public key
            public_key = self.get_public_key(kid)

            # Full Decode & Validate
            # Azure AD tokens use standard claims: aud (audience), exp (expiration), iss (issuer)
            options = {
                "verify_aud": True,
                "verify_iss": self.verify_issuer,
                "verify_exp": True,
            }

            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                options=options,
                issuer=self.expected_issuers if self.verify_issuer else None
            )

            # Check Scope permissions ('scp' or 'roles' claim)
            self._verify_claims_and_scopes(payload)

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer authorization token has expired"
            )
        except jwt.InvalidAudienceError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Resource audience mismatch. Expected: {self.client_id}"
            )
        except jwt.InvalidIssuerError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed: Identity issuer domain is invalid"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Bearer authorization token is malformed or invalid: {str(e)}"
            )

    def _verify_claims_and_scopes(self, payload: Dict):
        """Verifies if token has the required permissions/scp claim."""
        # Azure AD standard scopes typically map to 'scp' (Client Flow / User Impersonation) 
        # or 'roles' (App Registrations Client Credentials Flow)
        token_scopes = payload.get("scp", "")
        token_roles = payload.get("roles", [])

        allowed = False
        
        # Scope is space-delimited string
        scopes_list = [s.strip() for s in token_scopes.split(" ")] if token_scopes else []
        
        # Check against simple scope name or full URI scope
        short_scope = self.required_scope.split("/")[-1]
        
        if self.required_scope in scopes_list or short_scope in scopes_list:
            allowed = True
        elif self.required_scope in token_roles or short_scope in token_roles:
            allowed = True
            
        if not allowed:
            logger.warning(f"Unprivileged token scopes: scp={token_scopes}, roles={token_roles}. Expected scope: {self.required_scope}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Target scope '{self.required_scope}' is unassigned."
            )


# Initialize our Singleton Verifier
verifierInstance = AzureADTokenVerifier()

async def verify_azure_ad_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """
    Dependency helper to secure FastAPI routes. Validates authorization headers.
    """
    return verifierInstance.verify_token(credentials.credentials)


async def get_token_query_param(request: Request) -> str:
    """
    Alternative query parameter provider, used specifically for Server-Sent Events (SSE)
    connections since standard EventSource browser API does not support custom headers.
    """
    token = request.query_params.get("token")
    if not token:
        # Check Authorization header as fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer credential verification token is missing. Provide via query param '?token='."
        )
        
    try:
        # Validate using our active verifier
        verifierInstance.verify_token(token)
        return token
    except HTTPException:
        # Re-raise standard unauthorized
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"SSE Security handshaking failed: {str(e)}"
        )
