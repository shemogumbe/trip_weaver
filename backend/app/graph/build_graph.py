"""
DEPRECATED: Legacy LangGraph builder.

This module now re-exports the async processor's build_graph() to maintain
backward compatibility while the system runs on the new async pipeline.

Use app.graph.async_processor.build_graph instead for direct imports.
"""

from app.graph.async_processor import build_graph  # re-export

__all__ = ["build_graph"]
