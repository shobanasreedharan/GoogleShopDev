from fastapi import FastAPI
from pydantic import BaseModel
from backend.core.registry import MCP_REGISTRY

app = FastAPI()


class MCPRequest(BaseModel):
    tool: str
    action: str
    payload: dict = {}


@app.post("/mcp")
def mcp_call(req: MCPRequest):
    return MCP_REGISTRY.execute(req.tool, req.action, req.payload)