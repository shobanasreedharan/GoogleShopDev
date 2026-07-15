from abc import ABC, abstractmethod
from typing import Any, Dict


class MCPTool(ABC):
    """
    Standard interface for ALL MCP tools (MongoDB, Maps, etc.)
    """

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def execute(self, action: str, payload: Dict[str, Any]) -> Any:
        pass