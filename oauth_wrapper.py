from fastmcp import FastMCP
from fastmcp.server import create_proxy
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
import secrets
import os

BASE_URL = os.environ.get("BASE_URL", "https://yargi-mcp-oauth.onrender.com")
UPSTREAM_MCP = "https://yargimcp.fastmcp.app/mcp"

mcp = create_proxy(UPSTREAM_MCP)

async def oauth_metadata(request):
    return JSONResponse({
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/authorize",
        "token_endpoint": f"{BASE_URL}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"]
    })

async def protected_resource(request):
    return JSONResponse({
        "resource": f"{BASE_URL}/mcp",
        "authorization_servers": [BASE_URL],
        "bearer_methods_supported": ["header"]
    })

async def authorize(request):
    params = dict(request.query_params)
    redirect_uri = params.get("redirect_uri", "")
    state = params.get("state", "")
    code = secrets.token_urlsafe(32)
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(url=f"{redirect_uri}{separator}code={code}&state={state}")

async def token(request):
    return JSONResponse({
        "access_token": secrets.token_urlsafe(32),
        "token_type": "bearer",
        "expires_in": 86400
    })

mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])(oauth_metadata)
mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])(protected_resource)
mcp.custom_route("/authorize", methods=["GET"])(authorize)
mcp.custom_route("/token", methods=["POST"])(token)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
