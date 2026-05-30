-------------------------------------------------------
mcp>=0.1.0
fastapi>=0.110.0
uvicorn>=0.28.0
pyjwt[crypto]>=2.8.0
requests>=2.31.0
----------------------------------------------------------

--------------------------------------------------
Run command : uvicorn app:app --host 0.0.0.0 --port 8000
---------------------------------------------------

import logging
import os
import sys
import jwt
import requests
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from mcp.server.fastmcp import FastMCP
from mcp.server.asgi import create_asgi_app

# =====================================================================
# 1. LOGGING & INITIALIZATION
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("azure-mcp-server")

# =====================================================================
# 2. CONFIGURATION & ENVIRONMENT VARIABLES
# =====================================================================
class Settings:
    TENANT_ID: str = os.environ.get("AZURE_TENANT_ID", "your-tenant-id")
    CLIENT_ID: str = os.environ.get("AZURE_CLIENT_ID", "your-client-id")
    
    # Entra ID OpenID Metadata configurations
    JWKS_URL: str = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
    ISSUER: str = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"

settings = Settings()
security = HTTPBearer()

# =====================================================================
# 3. AUTHENTICATION & TOKEN VALIDATION
# =====================================================================
def verify_azure_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Decodes and validates the Entra ID OAuth 2.0 Bearer Token.
    Ensures signature verification against Microsoft's dynamic keys, 
    expiration checking, issuer checking, and audience verification.
    """
    token = credentials.credentials
    try:
        # Fetch the Microsoft public JSON Web Key Set (JWKS)
        jwks = requests.get(settings.JWKS_URL, timeout=5).json()
        unverified_header = jwt.get_unverified_header(token)
        
        # Match token kid (Key ID) to the public key set
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
                
        if not rsa_key:
            logger.warning("Token verification failed: No matching public key found.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token signature metadata."
            )

        # Validate cryptographic signatures and target claims
        payload = jwt.decode(
            token,
            jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key),
            algorithms=["RS256"],
            audience=settings.CLIENT_ID,
            issuer=settings.ISSUER
        )
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Rejected request: Expired token presented.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired."
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Rejected request: Invalid token claims. Trace: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Internal security framework fault: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal Auth Validation Error."
        )

# =====================================================================
# 4. MCP SERVER INITIALIZATION & TOOLS DEFINITION
# =====================================================================
mcp_server = FastMCP(name="Azure-Secured-Enterprise-Server")

@mcp_server.tool()
def get_system_status(component_name: str) -> str:
    """
    Fetches the operational status of internal enterprise infrastructure.
    Args:
        component_name: Name of the subsystem (e.g., 'database', 'auth-api')
    """
    logger.info(f"Tool 'get_system_status' triggered for: {component_name}")
    return f"Component '{component_name}' is healthy and running optimally."

@mcp_server.tool()
def calculate_risk_score(revenue: float, country_code: str) -> dict:
    """
    Evaluates financial and geographic risk metrics for custom workflows.
    """
    logger.info(f"Tool 'calculate_risk_score' triggered.")
    base_risk = 10 if country_code.upper() in ["US", "CA", "GB"] else 40
    if revenue > 1000000:
        base_risk -= 5
    return {"risk_score": max(5, base_risk), "status": "Approved for processing"}

# =====================================================================
# 5. FASTAPI APPLICATION SETUP
# =====================================================================
app = FastAPI(
    title="Secured Azure MCP Endpoint Gateway", 
    description="A secure hosted Model Context Protocol wrapper protected by OAuth 2.0 via Microsoft Entra ID."
)

# Convert MCP hooks to standard ASGI application mapping
mcp_asgi_app = create_asgi_app(mcp_server)

@app.get("/mcp")
@app.post("/mcp")
async def handle_mcp_requests(payload: dict = Depends(verify_azure_token)):
    """
    Secured Gateway router mapping external requests directly into 
    the native MCP loop after successful JWT claims evaluation.
    """
    return await mcp_asgi_app

@app.get("/healthz", status_code=status.HTTP_200_OK)
def operational_health_check():
    """Unprotected health probe route for Azure App Service pinging."""
    return {"status": "online", "secured_tenant": settings.TENANT_ID}

# =====================================================================
# 6. EXPLICIT APPLICATION ENTRY-POINT
# =====================================================================
if __name__ == "__main__":
    import uvicorn
    
    # Read environment port for Azure compatibility (defaults to 8000 locally)
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"Starting Secured MCP Server on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)

---------------------------------------------------------
Once they obtain the token, they interact with your web app at the target endpoint:

URL: https://<your-azure-webapp-name>.azurewebsites.net/mcp

They must inject the token into the request header like this:

POST /mcp HTTP/1.1
Host: your-azure-webapp-name.azurewebsites.net
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Im...
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_system_status",
    "arguments": {
      "component_name": "database"
    }
  },
  "id": 1
}
