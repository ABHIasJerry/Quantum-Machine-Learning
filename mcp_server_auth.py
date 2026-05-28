"""
Custom MCP Server with OAuth 2.0 Authentication
Designed for Azure Web App deployment
"""

import json
import os
import logging
import asyncio
from typing import Any, Optional
from datetime import datetime, timedelta
import uuid

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import httpx
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== Configuration Models ====================

class ServerConfig(BaseModel):
    """Server configuration from environment variables"""
    client_id: str
    client_secret: str
    scope: str
    azure_tenant: Optional[str] = None
    server_port: int = 8000
    server_name: str = "custom-mcp-server"
    environment: str = "production"


class TokenCache:
    """Simple in-memory token cache"""
    def __init__(self):
        self.tokens: dict[str, dict] = {}
    
    def get(self, key: str) -> Optional[dict]:
        token_data = self.tokens.get(key)
        if token_data and token_data['expires_at'] > datetime.utcnow():
            return token_data['token']
        elif token_data:
            del self.tokens[key]
        return None
    
    def set(self, key: str, token: dict, expires_in: int):
        self.tokens[key] = {
            'token': token,
            'expires_at': datetime.utcnow() + timedelta(seconds=expires_in - 300)
        }


# ==================== OAuth 2.0 Handler ====================

class OAuth2Handler:
    """Handles OAuth 2.0 authentication with Azure AD or other providers"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.token_cache = TokenCache()
        self.token_endpoint = self._get_token_endpoint()
    
    def _get_token_endpoint(self) -> str:
        """Determine token endpoint based on configuration"""
        if self.config.azure_tenant:
            return f"https://login.microsoftonline.com/{self.config.azure_tenant}/oauth2/v2.0/token"
        # Default to Azure AD v2.0 endpoint
        return "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    async def get_access_token(self, code: str) -> dict:
        """Exchange authorization code for access token"""
        cache_key = f"token_{code[:10]}"
        cached = self.token_cache.get(cache_key)
        if cached:
            return cached
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data={
                    'client_id': self.config.client_id,
                    'client_secret': self.config.client_secret,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'scope': self.config.scope,
                }
            )
            response.raise_for_status()
            token_data = response.json()
            
            if 'access_token' in token_data:
                expires_in = token_data.get('expires_in', 3600)
                self.token_cache.set(cache_key, token_data, expires_in)
            
            return token_data
    
    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data={
                    'client_id': self.config.client_id,
                    'client_secret': self.config.client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token',
                    'scope': self.config.scope,
                }
            )
            response.raise_for_status()
            return response.json()
    
    def validate_token(self, token: str) -> bool:
        """Basic token validation (in production, implement JWT validation)"""
        return bool(token) and len(token) > 10


# ==================== Custom Tool Implementations ====================

class CustomToolHandler:
    """Implements custom MCP tools"""
    
    @staticmethod
    def echo_message(message: str) -> dict:
        """Echo tool - returns the message with metadata"""
        return {
            "status": "success",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "echo_id": str(uuid.uuid4())
        }
    
    @staticmethod
    def process_data(data: list, operation: str) -> dict:
        """Data processing tool - supports sum, avg, count operations"""
        if not isinstance(data, list):
            raise ValueError("Data must be a list")
        
        if operation == "sum":
            result = sum(float(x) for x in data)
        elif operation == "avg":
            result = sum(float(x) for x in data) / len(data) if data else 0
        elif operation == "count":
            result = len(data)
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        return {
            "status": "success",
            "operation": operation,
            "result": result,
            "data_count": len(data)
        }
    
    @staticmethod
    def text_transform(text: str, transform_type: str) -> dict:
        """Text transformation tool"""
        if transform_type == "uppercase":
            result = text.upper()
        elif transform_type == "lowercase":
            result = text.lower()
        elif transform_type == "reverse":
            result = text[::-1]
        elif transform_type == "word_count":
            result = len(text.split())
        else:
            raise ValueError(f"Unknown transform: {transform_type}")
        
        return {
            "status": "success",
            "transform_type": transform_type,
            "result": result,
            "input_length": len(text)
        }
    
    @staticmethod
    def get_system_info() -> dict:
        """System information tool"""
        return {
            "status": "success",
            "server_name": os.getenv('WEBSITE_INSTANCE_ID', 'local-dev'),
            "environment": os.getenv('WEBSITE_ENVIRONMENT', 'development'),
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "1.0.0"
        }


# ==================== Request/Response Models ====================

class ToolCall(BaseModel):
    """MCP Tool call request"""
    tool_name: str
    arguments: dict[str, Any]


class ToolResponse(BaseModel):
    """MCP Tool response"""
    result: dict
    error: Optional[str] = None


class AuthRequest(BaseModel):
    """OAuth authentication request"""
    code: str
    redirect_uri: Optional[str] = None


class AuthResponse(BaseModel):
    """OAuth authentication response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None


# ==================== FastAPI Application ====================

@lru_cache
def get_config() -> ServerConfig:
    """Load configuration from environment"""
    return ServerConfig(
        client_id=os.getenv('OAUTH_CLIENT_ID', ''),
        client_secret=os.getenv('OAUTH_CLIENT_SECRET', ''),
        scope=os.getenv('OAUTH_SCOPE', 'api://default'),
        azure_tenant=os.getenv('AZURE_TENANT_ID'),
        server_port=int(os.getenv('PORT', 8000)),
        environment=os.getenv('ENVIRONMENT', 'production')
    )


def create_app(config: Optional[ServerConfig] = None) -> FastAPI:
    """Create and configure FastAPI application"""
    if config is None:
        config = get_config()
    
    app = FastAPI(
        title="Custom MCP Server",
        description="OAuth 2.0 enabled Model Context Protocol Server",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize handlers
    oauth_handler = OAuth2Handler(config)
    tool_handler = CustomToolHandler()
    
    # Store tokens by request ID (in production, use Redis or database)
    request_tokens: dict[str, str] = {}
    
    # ==================== Authentication Routes ====================
    
    @app.post("/auth/authorize", response_model=dict)
    async def authorize():
        """Generate authorization URL for clients"""
        auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        params = {
            'client_id': config.client_id,
            'response_type': 'code',
            'scope': config.scope,
            'redirect_uri': os.getenv('REDIRECT_URI', 'http://localhost:3000/callback')
        }
        return {
            "auth_url": auth_url,
            "params": params
        }
    
    @app.post("/auth/token", response_model=AuthResponse)
    async def get_token(request: AuthRequest):
        """Exchange authorization code for access token"""
        try:
            token_data = await oauth_handler.get_access_token(request.code)
            logger.info(f"Token exchange successful")
            return AuthResponse(
                access_token=token_data['access_token'],
                expires_in=token_data.get('expires_in', 3600),
                refresh_token=token_data.get('refresh_token'),
            )
        except Exception as e:
            logger.error(f"Token exchange failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/auth/refresh")
    async def refresh_token(refresh_token: str):
        """Refresh access token"""
        try:
            token_data = await oauth_handler.refresh_access_token(refresh_token)
            return AuthResponse(
                access_token=token_data['access_token'],
                expires_in=token_data.get('expires_in', 3600),
                refresh_token=token_data.get('refresh_token'),
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Token refresh failed")
    
    # ==================== Token Validation ====================
    
    async def verify_token(authorization: str = Header(None)) -> str:
        """Verify and extract token from Authorization header"""
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=401, detail="Invalid authorization scheme")
            
            if not oauth_handler.validate_token(token):
                raise HTTPException(status_code=401, detail="Invalid token")
            
            return token
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    # ==================== Tool Routes ====================
    
    @app.get("/tools")
    async def list_tools(token: str = Depends(verify_token)):
        """List available tools (requires authentication)"""
        return {
            "tools": [
                {
                    "name": "echo_message",
                    "description": "Echo a message back with metadata",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Message to echo"}
                        },
                        "required": ["message"]
                    }
                },
                {
                    "name": "process_data",
                    "description": "Process numeric data with various operations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "array", "description": "Array of numbers"},
                            "operation": {"type": "string", "enum": ["sum", "avg", "count"]}
                        },
                        "required": ["data", "operation"]
                    }
                },
                {
                    "name": "text_transform",
                    "description": "Transform text in various ways",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "transform_type": {
                                "type": "string",
                                "enum": ["uppercase", "lowercase", "reverse", "word_count"]
                            }
                        },
                        "required": ["text", "transform_type"]
                    }
                },
                {
                    "name": "get_system_info",
                    "description": "Get system information",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        }
    
    @app.post("/tools/call", response_model=ToolResponse)
    async def call_tool(tool_call: ToolCall, token: str = Depends(verify_token)):
        """Call a specific tool"""
        try:
            logger.info(f"Tool call: {tool_call.tool_name} with args: {tool_call.arguments}")
            
            if tool_call.tool_name == "echo_message":
                result = tool_handler.echo_message(tool_call.arguments['message'])
            elif tool_call.tool_name == "process_data":
                result = tool_handler.process_data(
                    tool_call.arguments['data'],
                    tool_call.arguments['operation']
                )
            elif tool_call.tool_name == "text_transform":
                result = tool_handler.text_transform(
                    tool_call.arguments['text'],
                    tool_call.arguments['transform_type']
                )
            elif tool_call.tool_name == "get_system_info":
                result = tool_handler.get_system_info()
            else:
                return ToolResponse(
                    result={},
                    error=f"Unknown tool: {tool_call.tool_name}"
                )
            
            return ToolResponse(result=result)
        
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return ToolResponse(
                result={},
                error=str(e)
            )
    
    # ==================== Health & Info Routes ====================
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "server": config.server_name
        }
    
    @app.get("/info")
    async def server_info():
        """Server information endpoint"""
        return {
            "name": config.server_name,
            "version": "1.0.0",
            "environment": config.environment,
            "oauth_enabled": bool(config.client_id),
            "auth_endpoint": "/auth/token",
            "tools_endpoint": "/tools",
            "call_tool_endpoint": "/tools/call"
        }
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Custom MCP Server",
            "documentation": "/docs",
            "info": "/info"
        }
    
    return app


# ==================== Server Startup ====================

if __name__ == "__main__":
    config = get_config()
    
    # Validate configuration
    if not config.client_id or not config.client_secret:
        logger.warning("OAuth configuration not found. Running without authentication.")
    
    app = create_app(config)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.server_port,
        log_level="info"
    )
    
    