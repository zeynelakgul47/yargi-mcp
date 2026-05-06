from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
import uvicorn
import secrets
import httpx
import os

app = FastAPI()

BASE_URL = os.environ.get("BASE_URL", "https://yargi-mcp-oauth.onrender.com")
UPSTREAM_MCP = "https://yargimcp.fastmcp.app/mcp"

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

@app.post("/token")
async def token(request: Request):
    return JSONResponse({
        "access_token": secrets.token_urlsafe(32),
        "token_type": "bearer",
        "expires_in": 86400
    })

@app.api_route("/mcp", methods=["GET", "POST", "DELETE", "PUT", "PATCH"])
@app.api_route("/mcp/{path:path}", methods=["GET", "POST", "DELETE", "PUT", "PATCH"])
async def mcp_proxy(request: Request, path: str = ""):
    url = f"{UPSTREAM_MCP}/{path}" if path else UPSTREAM_MCP
    
    body = await request.body()
    
    headers = {}
    for k, v in request.headers.items():
        if k.lower() not in ["host", "authorization", "content-length", "transfer-encoding"]:
            headers[k] = v
    
    accept = request.headers.get("accept", "")
    is_sse = "text/event-stream" in accept
    
    try:
        if is_sse:
            async def stream():
                async with httpx.AsyncClient(timeout=60) as client:
                    async with client.stream(
                        method=request.method,
                        url=url,
                        content=body,
                        headers=headers,
                        params=dict(request.query_params)
                    ) as resp:
                        async for chunk in resp.aiter_bytes():
                            yield chunk
            return StreamingResponse(stream(), media_type="text/event-stream")
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(
                    method=request.method,
                    url=url,
                    content=body,
                    headers=headers,
                    params=dict(request.query_params)
                )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json")
            )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
