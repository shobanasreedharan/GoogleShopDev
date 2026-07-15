from dotenv import load_dotenv
load_dotenv()

import os
import json
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from backend.agent.agent import create_agent
from auth import get_current_user
import time

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://smartcart-mcp-505176174078.us-central1.run.app/mcp")

session_service = InMemorySessionService()
APP_NAME = "smartcart"
runner = None


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        req_id = int(time.time() * 1000)

        # Step 1: Initialize
        init_res = await client.post(MCP_SERVER_URL,
            headers={"Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": req_id, "method": "initialize",
                  "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                             "clientInfo": {"name": "smartcart-agent", "version": "1.0"}}}
        )
        print(f"[MCP] init status: {init_res.status_code}, headers: {dict(init_res.headers)}")
        print(f"[MCP] init body: {init_res.text[:500]}")

        session_id = init_res.headers.get("mcp-session-id")
        if not session_id:
            raise ValueError(f"No mcp-session-id in init response. Headers: {dict(init_res.headers)}")

        # Step 2: Notify initialized
        notif_res = await client.post(MCP_SERVER_URL,
            headers={"Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream",
                     "mcp-session-id": session_id},
            json={"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        print(f"[MCP] notif status: {notif_res.status_code}, body: {notif_res.text[:200]}")

        # Step 3: Call tool
        tool_res = await client.post(MCP_SERVER_URL,
            headers={"Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream",
                     "mcp-session-id": session_id},
            json={"jsonrpc": "2.0", "id": req_id + 1, "method": "tools/call",
                  "params": {"name": tool_name, "arguments": arguments}}
        )
        print(f"[MCP] tool status: {tool_res.status_code}")
        print(f"[MCP] tool body: {tool_res.text[:1000]}")

        # Parse SSE — handle both \n and \r\n
        for line in tool_res.text.splitlines():
            line = line.strip()
            if line.startswith("data: "):
                raw = line[6:].strip()
                if not raw or raw == "[DONE]":
                    continue
                data = json.loads(raw)
                if "error" in data:
                    raise ValueError(f"MCP tool error: {data['error']}")
                result = data.get("result", {})
                content = result.get("content", [])
                if content:
                    return json.loads(content[0].get("text", "{}"))
        return {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner
    agent = create_agent()
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str
    # user_id intentionally removed — derived from verified Firebase token only

@app.post("/chat")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    uid = user["uid"]  # verified, not client-supplied

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=uid, session_id=req.session_id,
    )
    if not session:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=uid, session_id=req.session_id,
        )

    pantry_data = await call_mcp_tool("get_pantry_items", {"user_id": uid})

    enriched_message = f"""User's pantry data from database: {pantry_data}

User question: {req.message}

Answer the user's question using the pantry data above. Be concise and helpful."""

    user_message = Content(parts=[Part(text=enriched_message)])
    final_response = ""

    async for event in runner.run_async(
        user_id=uid,
        session_id=req.session_id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    final_response += part.text

    return {"response": final_response, "session_id": req.session_id}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug/tools")
async def debug_tools():
    try:
        from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
        toolset = MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=MCP_SERVER_URL,
                timeout=60,
            )
        )
        tools = await toolset.get_tools()
        return {"tools": [t.name for t in tools], "count": len(tools)}
    except Exception as e:
        return {"error": str(e)}

# NOTE: /debug/pantry/{user_id} was removed — it let anyone query any
# user's pantry by guessing their uid, with no auth check, against live
# Firestore data. If you need a debug route, protect it the same way as
# /chat (Depends(get_current_user)) and use the verified uid only — never
# accept an arbitrary user_id from the URL.
@app.get("/debug/pantry/me")
async def debug_pantry_me(user: dict = Depends(get_current_user)):
    try:
        result = await call_mcp_tool("get_pantry_items", {"user_id": user["uid"]})
        return {"result": result, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}
