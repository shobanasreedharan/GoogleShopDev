import json
from typing import Any


def mcp_success(data: Any) -> dict:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(data, default=str)
            }
        ],
        "isError": False
    }


def mcp_error(message: str) -> dict:
    return {
        "content": [
            {
                "type": "text",
                "text": message
            }
        ],
        "isError": True
    }