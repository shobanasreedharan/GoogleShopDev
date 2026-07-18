"""Compatibility entry point for deployments that import main:app.

The canonical FastAPI application lives in backend.api.main.
"""

from backend.api.main import app

__all__ = ["app"]
