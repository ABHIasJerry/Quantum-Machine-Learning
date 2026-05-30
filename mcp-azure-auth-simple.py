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

import os
import jwt
import requests
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from mcp.server.fastmcp import FastMCP
from mcp.server.asgi import create_asgi_app

# 1. Configuration & Credentials (Injected via Azure App Service Env Variables)
TENANT_ID = os.environ.get("AZURE_TENANT_ID", "your-tenant-id")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "your-client-id")

# Fetch OpenID Configuration dynamically from Azure Entra ID to get signing keys
JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"

security = HTTPBearer()

# 2. Token Verification Dependency
def verify_azure_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validates the incoming Entra ID JWT Token."""
    token = credentials.credentials
    try:
        # Get public keys from Microsoft to verify signature
        jwks = requests.get(JWKS_URL).json()
        unverified_header = jwt.get_unverified_header(token)
        
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
                
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid token signature headers.")

        # Validate signature, expiration, audience (Client ID), and issuer
        payload = jwt.decode(
            token,
            jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key),
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=ISSUER
        )
        return payload  # Contains user / app identities if needed by tools

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Auth Validation Error.")


# 3. Define the MCP Server and Custom Tools
# We use FastMCP for modern helper abstractions
mcp_server = FastMCP(name="Azure-Secured-Enterprise-Server")

@mcp_server.tool()
def get_system_status(component_name: str) -> str:
    """
    Fetches the operational status of internal infrastructure components.
    Args:
        component_name: Name of the subsystem (e.g., 'database', 'auth-api')
    """
    # Custom business logic here
    return f"Component '{component_name}' is healthy and running optimally."

@mcp_server.tool()
def calculate_risk_score(revenue: float, country_code: str) -> dict:
    """
    Evaluates compliance and financial risk scores for a prospective deal.
    """
    base_risk = 10 if country_code.upper() in ["US", "CA", "GB"] else 40
    if revenue > 1000000:
        base_risk -= 5
    return {"risk_score": max(5, base_risk), "status": "Approved for processing"}


# 4. Integrate MCP with FastAPI & Apply Authentication Guard
app = FastAPI(title="Secured Azure MCP Endpoint")

# Generate standard MCP ASGI endpoints (/sse, /messages, or /tools)
mcp_asgi_app = create_asgi_app(mcp_server)

# Wrap the endpoint in FastAPI with our verify_azure_token dependency
@app.get("/mcp")
@app.post("/mcp")
async def handle_mcp_requests(payload: dict = Depends(verify_azure_token)):
    """
    Secured Gateway router routing external AI requests to our MCP server
    only if the Entra ID authorization passes.
    """
    # Forward the incoming request context to the underlying MCP router
    return await mcp_asgi_app

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
