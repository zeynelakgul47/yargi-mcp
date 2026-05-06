from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
import uvicorn
import secrets
import httpx
import os

app = FastAPI()

BASE_URL = os.environ.get("BASE_URL", "https://yargi-mcp-oauth.onrender.com")
UPSTREAM_MCP = "https://yargimcp.fastmcp.app/mcp"

# OAuth Discovery
@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    return JSONResponse({
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/authorize",
        "token_endpoint": f"{BASE_URL}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"]
    })

@app.get("/.well-known/oauth-protected-resource")
async def protected_resource():
    return JSONResponse({
        "resource": f"{BASE_URL}/mcp",
        "authorization_servers": [BASE_URL],
        "bearer_methods_supported": ["header"]
    })

# OAuth Authorize — anında code üretir, gerçek login yok
@app.get("/authorize")
async def authorize(
    response_type: str = "code",
    client_id: str = "",
    redirect_uri: str = "",
    state: str = "",
    code_challenge: str = "",
    code_challenge_method: str = ""
):
    code = secrets.token_urlsafe(32)
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        url=f"{redirect_uri}{separator}code={code}&state={state}"
    )

# OAuth Token — her code için geçerli token üretir
@app.post("/token")
async def token(request: Request):
    return JSONResponse({
        "access_token": secrets.token_urlsafe(32),
        "token_type": "bearer",
        "expires_in": 86400
    })

# MCP Proxy — Yargı MCP'ye yönlendirir
@app.api_route("/mcp", methods=["GET", "POST", "DELETE"])
@app.api_route("/mcp/{path:path}", methods=["GET", "POST", "DELETE"])
async def mcp_proxy(request: Request, path: str = ""):
    url = UPSTREAM_MCP
    if path:
        url = f"{UPSTREAM_MCP}/{path}"
    
    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ["host", "authorization", "content-length"]
    }
    headers["accept"] = "application/json, text/event-stream"
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            content=body,
            headers=headers,
            params=dict(request.query_params)
        )
    
    return JSONResponse(
        content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {},
        status_code=resp.status_code,
        headers={"content-type": resp.headers.get("content-type", "application/json")}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
