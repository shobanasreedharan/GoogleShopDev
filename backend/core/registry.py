import time
from typing import Any, Dict


class MCPRegistry:

    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.execution_log = []

    def register(self, name: str, tool: Any):
        self.tools[name] = tool
        print(f"[MCP] Registered tool: {name}")

    def execute(self, tool_name: str, action: str, payload: Dict[str, Any]):

        start = time.time()

        tool = self.tools.get(tool_name)

        if not tool:
            raise Exception(f"Tool not found: {tool_name}")

        try:
            result = tool.execute(action, payload)

            self._log(tool_name, action, True, time.time() - start)
            return result

        except Exception as e:
            self._log(tool_name, action, False, time.time() - start, str(e))
            print(f"[MCP ERROR] {tool_name}.{action}: {e}")
            return {"error": str(e)}

    def _log(self, tool, action, success, latency, error=None):
        self.execution_log.append({
            "tool": tool,
            "action": action,
            "success": success,
            "latency_ms": round(latency * 1000, 2),
            "error": error,
        })


MCP_REGISTRY = MCPRegistry()

# REGISTER TOOL
from backend.mcp.mongo_tools import MongoTools
MCP_REGISTRY.register("mongo", MongoTools())