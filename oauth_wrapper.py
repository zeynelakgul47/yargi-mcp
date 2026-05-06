from fastmcp import FastMCP
import os

BASE_URL = os.environ.get("BASE_URL", "https://yargi-mcp-oauth.onrender.com")
UPSTREAM_MCP = "https://yargimcp.fastmcp.app/mcp"

mcp = FastMCP.as_proxy(UPSTREAM_MCP)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
