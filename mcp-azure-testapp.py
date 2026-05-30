---------------------------------------------------------------------
export AZURE_TENANT_ID="xxxx-xxxx-xxxx"
export AZURE_CLIENT_ID="xxxx-xxxx-xxxx"
export AZURE_CLIENT_SECRET="your_actual_secret_value"
export MCP_SERVER_URL="https://your-azure-webapp.azurewebsites.net/mcp"
----------------------------------------------------------------------

import json
import os
import sys
import requests

# =====================================================================
# 1. CONFIGURATION
# =====================================================================
# Replace these with your actual Azure Entra ID and deployment credentials
TENANT_ID = os.environ.get("AZURE_TENANT_ID", "your-tenant-id")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "your-client-id")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "your-client-secret")

# Target Hosted Azure Web App MCP URL
# Local testing default: "http://localhost:8000/mcp"
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "https://your-webapp.azurewebsites.net/mcp")

# =====================================================================
# 2. OAUTH 2.0 TOKEN ACQUISITION
# =====================================================================
def get_azure_access_token() -> str:
    """Performs an OAuth 2.0 Client Credentials Grant flow against Entra ID."""
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    
    # Crucial: The scope must target your application ID URI
    # For an App Registration acting as its own API, use the client ID scope format:
    scope = f"api://{CLIENT_ID}/.default"
    
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": scope
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    print(f"Requesting Access Token from Entra ID for scope: {scope}...")
    response = requests.post(token_url, data=payload, headers=headers, timeout=10)
    
    if response.status_code != 200:
        print(f"[-] Token Request Failed: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    token_data = response.json()
    print("[+] Access token successfully acquired.")
    return token_data["access_token"]

# =====================================================================
# 3. SECURED MCP EXECUTION FLOW
# =====================================================================
def call_mcp_tool(token: str):
    """Sends a standardized JSON-RPC request to the secured MCP tool route."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Standard MCP Client JSON-RPC payload format for a tool execution
    mcp_payload = {
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
    
    print(f"\nDispatching payload to MCP Server at: {MCP_SERVER_URL}")
    try:
        response = requests.post(MCP_SERVER_URL, json=mcp_payload, headers=headers, timeout=15)
        
        print(f"Server Response Code: {response.status_code}")
        if response.status_code == 200:
            print("[+] Success! MCP Tool execution output:")
            print(json.dumps(response.json(), indent=2))
        elif response.status_code == 401:
            print("[-] Unauthorized! Token verification failed on the server.")
            print(response.text)
        else:
            print(f"[-] Request failed with status code {response.status_code}:")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"[-] Network connection error: {str(e)}")

# =====================================================================
# RUN SCRIPT
# =====================================================================
if __name__ == "__main__":
    # Fallback sanity check
    if "your-" in f"{TENANT_ID}{CLIENT_ID}{CLIENT_SECRET}":
        print("[-] Please configure your real Azure environment variables or update the strings in the script.")
        sys.exit(1)
        
    access_token = get_azure_access_token()
    call_mcp_tool(access_token)
