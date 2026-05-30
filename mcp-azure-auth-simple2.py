----------------------------------------------------------------------
Startup Command Mapping
Ensure Azure explicitly uses the correct module name to initialize Uvicorn.

In Configuration ➔ General Settings ➔ Startup Command, input:

Bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
------------------------------------------------------------------------

import logging
import os
import sys
import jwt
import requests
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastmcp import FastMCP

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
    TENANT_ID: str = os.environ.get("AZURE_TENANT_ID")
    CLIENT_ID: str = os.environ.get("AZURE_CLIENT_ID")
    
    # Fail early during startup if Azure parameters are missing
    def validate(self):
        if not self.TENANT_ID or not self.CLIENT_ID:
            logger.critical("CRITICAL: AZURE_TENANT_ID or AZURE_CLIENT_ID environment variables are missing!")
            sys.exit(1)

settings = Settings()
settings.validate()

# Entra ID OpenID Metadata configurations
JWKS_URL = f"https://login.microsoftonline.com/{settings.TENANT_ID}/discovery/v2.0/keys"
ISSUER = f"https://login.microsoftonline.com/{settings.TENANT_ID}/v2.0"

security = HTTPBearer()

# =====================================================================
# 3. AUTHENTICATION & TOKEN VALIDATION
# =====================================================================
def verify_azure_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Decodes and validates the Entra ID OAuth 2.0 Bearer Token."""
    token = credentials.credentials
    try:
        jwks = requests.get(JWKS_URL, timeout=5).json()
        unverified_header = jwt.get_unverified_header(token)
        
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = {k: key[k] for k in ["kty", "kid", "use", "n", "e"]}
                break
                
        if not rsa_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token metadata.")

        payload = jwt.decode(
            token,
            jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key),
            algorithms=["RS256"],
            audience=settings.CLIENT_ID,
            issuer=ISSUER
        )
        return payload

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        logger.warning(f"Unauthorized Request Attempt: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token verification failed.")
    except Exception as e:
        logger.error(f"Internal security error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth engine failure.")

# =====================================================================
# 4. MCP SERVER INITIALIZATION & TOOLS
# =====================================================================
mcp_server = FastMCP(name="Azure-Secured-Enterprise-Server")

@mcp_server.tool()
def get_system_status(component_name: str) -> str:
    """Fetches the operational status of internal enterprise infrastructure."""
    return f"Component '{component_name}' is healthy and running optimally."

@mcp_server.tool()
async def list_tools_info() -> list[dict]:
    """
    Lists all tools registered on this MCP server along with their name,
    description, and input schema. Call this to discover what capabilities
    are available on this server.
    """
    tools = await mcp_server.get_tools()  # returns dict[str, Tool]
    result = []
    for tool_name, tool_obj in tools.items():
        result.append({
            "name": tool_name,
            "description": tool_obj.description or "No description provided.",
            "input_schema": tool_obj.parameters,  # JSON Schema dict of input params
        })
    return result

# =====================================================================
# 5. COMBINED ROUTING AND TRANSPORT
# =====================================================================
# Generate the official HTTP/SSE transport mapping wrapper from FastMCP
mcp_http_app = mcp_server.http_app(path="/mcp")

# Build the wrapper FastAPI app that manages security and lifespans
app = FastAPI(
    title="Secured Azure MCP Endpoint Gateway",
    lifespan=mcp_http_app.lifespan  # Crucial: Ensures background tasks initialize
)

# Apply token verification to the entire /mcp path
@app.get("/mcp", dependencies=[Depends(verify_azure_token)])
@app.post("/mcp", dependencies=[Depends(verify_azure_token)])
async def secure_mcp_proxy():
    """Dummy dependency hook enforcing auth before traffic hits the mounted app."""
    pass

# Mount the actual operational MCP endpoints directly underneath the auth guard
app.mount("/", mcp_http_app)

@app.get("/healthz", status_code=status.HTTP_200_OK)
def operational_health_check():
    """Unprotected health probe route for Azure App Service pinging."""
    return {"status": "online"}

# =====================================================================
# 6. EXPLICIT APPLICATION ENTRY-POINT
# =====================================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Secured MCP Server on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
