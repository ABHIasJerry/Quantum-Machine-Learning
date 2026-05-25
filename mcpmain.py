requirements------------------
fastapi>=0.100.0
uvicorn>=0.22.0
mcp>=1.0.0
pyjwt[crypto]>=2.8.0
requests>=2.31.0
python-dotenv>=1.0.0
cryptography>=41.0.0

startup commands---------------------
dev (uvicorn) -> uvicorn main:app --host 0.0.0.0 --port 8080
prod (gunicorn) -> gunicorn --bind=0.0.0.0 --workers=4 --worker-class=uvicorn.workers.UvicornWorker main:app

import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load local environment variables BEFORE initializing other modules
load_dotenv()

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

# Import FastMCP and SseServerTransport from modelcontextprotocol python package
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

# Import Azure AD Validation dependencies
from auth import verify_azure_ad_token, get_token_query_param, verifierInstance

# Setup Logging
logger = logging.getLogger("fastmcp_server")
logging.basicConfig(level=logging.INFO)

# ------------------------------------------------------------------------------
# 1. Initialize FastMCP Server with Tools and Prompts
# ------------------------------------------------------------------------------
mcp = FastMCP(
    "Cloud Operations MCP Server",
    description="Asynchronous Model Context Protocol (MCP) server providing cloud diagnostics, execution pipelines, and security automation tools."
)

# --- MCP Tool 1: Cloud System Metrics Diagnostics ---
@mcp.tool()
async def analyze_system_resource(resource_type: str = "all") -> str:
    """
    Returns simulated telemetry diagnostics for system cloud units (CPU, Memory, Disk, network).
    Useful to verify server-side asynchronous execution pipelines.
    
    Args:
        resource_type: Must be 'cpu', 'memory', 'disk', 'network', or 'all'
    """
    resource_type_lower = resource_type.lower()
    if resource_type_lower not in ["cpu", "memory", "disk", "network", "all"]:
        return f"Warning: Invalid resource type '{resource_type}'. Defaulting to 'all'."
        
    metrics = {
        "cpu": "CPU Load: 42.8% (User: 30%, System: 12.8%) | Tasks: 128 active",
        "memory": "RAM: Used 8.42 GB / Total 16.00 GB (Available: 7.58 GB) | Buffers/Cache: 3.12 GB",
        "disk": "IOPS Write: 1240/s | IOPS Read: 420/s | Disk Space: 62% Free",
        "network": "Ingress: 4.8 MB/s | Egress: 1.2 MB/s | Latency to Azure Hub: 14ms"
    }
    
    if resource_type_lower == "all":
        details = "\n".join([f"- [{k.upper()}] {v}" for k, v in metrics.items()])
        return f"### [SYSTEM MONITOR DATA]\nAll indicators reports normal:\n{details}"
        
    return f"### [RESOURCE INDICATOR]: {resource_type.upper()}\n{metrics[resource_type_lower]}"


# --- MCP Tool 2: Azure DevOps Deployment Status Inspector ---
@mcp.tool()
async def fetch_deployment_pipelines(project_name: str, limit: int = 5) -> str:
    """
    Inspects and gets status of production deployment pipelines. Shows active status, author, duration, and error codes.
    
    Args:
        project_name: Name of the repository e.g., 'portal-frontend', 'payment-gateway-service'
        limit: Number of history items to show (default 5)
    """
    pipelines_log = [
        {"id": "DEP-9042", "env": "Production", "status": "Success", "duration": "4m 12s", "trigger": "Git Push (main)", "author": "devops-auto-bot"},
        {"id": "DEP-9039", "env": "Staging", "status": "Success", "duration": "3m 48s", "trigger": "Git Push (main)", "author": "abhinaba.g"},
        {"id": "DEP-9031", "env": "Production", "status": "Failed (E-104)", "duration": "1m 15s", "trigger": "API Webhook", "author": "systems-pipeline"},
        {"id": "DEP-9028", "env": "Dev-Integration", "status": "Success", "duration": "2m 50s", "trigger": "Git Pull Request", "author": "qa-reviewer"},
        {"id": "DEP-9022", "env": "Performance-Sandbox", "status": "Stopped", "duration": "12s", "trigger": "Manual Cancellation", "author": "lead-architect"}
    ]
    
    # Filter by limit
    selected_logs = pipelines_log[:min(limit, len(pipelines_log))]
    formatted_rows = []
    for log in selected_logs:
        status_color = "🟢" if "Success" in log["status"] else ("🔴" if "Failed" in log["status"] else "🟡")
        formatted_rows.append(
            f"| {log['id']} | {log['env']} | {status_color} {log['status']} | {log['duration']} | {log['trigger']} | {log['author']} |"
        )
        
    markdown_output = (
        f"### Pipelines history for: {project_name}\n"
        f"| Pipeline ID | Target Env | Execution Status | Duration | Trigger Type | Triggered By |\n"
        f"| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        + "\n".join(formatted_rows)
    )
    return markdown_output


# --- MCP Tool 3: Secure Secrets Rotation Trigger ---
@mcp.tool()
async def rotate_server_secret(key_vault_name: str, secret_name: str) -> str:
    """
    Simulates a secure credentials rotation action inside Key Vault database.
    Requires server-side asynchronous task validation.
    
    Args:
        key_vault_name: Target Vault name, e.g. 'kv-prod-southeast'
        secret_name: Identifier of secret to update, e.g. 'DB_CONNECTION_STRING'
    """
    import datetime
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"✅ [SUCCESSFUL ROTATION OPERATION]\n"
        f"Vault Reference: {key_vault_name}\n"
        f"Updated Secret Entry: '{secret_name}'\n"
        f"Trigger Timestamp: {now_str}\n"
        f"Status: New cryptographic version provisioned. Old tokens marked for expiration (TTL: 24h)."
    )


# --- MCP Custom Prompt Example ---
@mcp.prompt()
def mcp_diagnose_issue(error_log: str) -> str:
    """Help user debug a generic system failure using system resources diagnostics."""
    return f"Review the following service error log, then run analyze_system_resource(resource_type='all') or fetch_deployment_pipelines to cross-examine system limits. \n\nError Log: {error_log}"


# ------------------------------------------------------------------------------
# 2. Setup FastAPI App & SECURE Endpoints
# ------------------------------------------------------------------------------
app = FastAPI(
    title="Secure FastAPI FastMCP Server",
    description="Deployment-ready Model Context Protocol (MCP) server bound with FastAPI and secured with Azure AD OAuth 2.0 validation.",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production according to your app host
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard SSE server-transport declaration
# This coordinates client SSE message channels
sse = SseServerTransport("/messages")

@app.get("/")
async def root_index():
    return {
        "status": "online",
        "protocol": "Model Context Protocol (MCP) v1.0",
        "engine": "FastMCP Python (Anthropic)",
        "security": "Enforced with Azure Active Directory (Microsoft Entra ID) OAuth 2.0 Authentication",
        "endpoints": {
            "oauth_jwks_discovery": verifierInstance.jwks_url,
            "sse_transport_handshake": "/sse?token=<jwt-token>",
            "sse_messages_callback": "/messages",
            "health_check": "/health"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/sse")
async def handle_sse(
    request: Request,
    token: str = Depends(get_token_query_param)
):
    """
    Primary SSE handshaking stream connection.
    Secured using OAuth token validation via the 'get_token_query_param' dependency.
    Clients connect to this endpoint to receive the server event-source flow.
    """
    logger.info(f"SSE client subscription received. Token validated successfully.")
    
    async with sse.connect_retrying(
        request.scope,
        request.receive,
        request._send
    ) as (read_stream, write_stream):
        # Bind connection streams directly with FastMCP protocol execution engine
        await mcp.server.handle_connection(read_stream, write_stream)


@app.post("/messages")
async def handle_messages(
    request: Request,
    token: Dict = Depends(verify_azure_ad_token)
):
    """
    Primary callback target for JSON-RPC messages from MCP client hosts.
    Endpoint is secured by requiring a Bearer JWT Token in headers.
    """
    logger.info("JSON-RPC message batch received via HTTP POST. Security claims verified.")
    
    # Process message payloads through standard SSE transport loop
    await sse.handle_post_message(
        request.scope,
        request.receive,
        request._send
    )


# ------------------------------------------------------------------------------
# 3. Server Startup Entry Point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"Bootstrapping Secure FastMCP ASGI Server at http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
