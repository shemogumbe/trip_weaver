"""
ASYNC TRIP PROCESSOR - Bypasses LangGraph for true parallel execution

This module provides a simple async-based trip processing function that gives us
dramatic speed improvements without the complexity and concurrency issues of LangGraph.
"""

import asyncio
from app.graph.state import RunState
from app.graph.agents import process_trip_async

def build_async_processor():
    """
    Returns an async function that processes trips in parallel.
    This replaces the LangGraph approach with simple, fast async execution.
    """
    async def process_trip(state: RunState) -> dict:
        """Process a trip request using true async parallelism"""
        result_state = await process_trip_async(state)

        # Return in the same format as LangGraph for compatibility
        return {
            "plan": result_state.plan,
            "artifacts": result_state.artifacts,
            "logs": result_state.logs,
            "prefs": result_state.prefs,
        }

    return process_trip

def build_sync_processor():
    """
    Returns a synchronous wrapper around the async processor for compatibility
    """
    async_processor = build_async_processor()
    
    def process_trip_sync(state: RunState) -> dict:
        """Synchronous wrapper that runs the async processor"""
        return asyncio.run(async_processor(state))
    
    return process_trip_sync

class _GraphLike:
    """Lightweight wrapper to mimic LangGraph's invoke/ainvoke interface."""

    def __init__(self, sync_fn, async_fn):
        self._sync_fn = sync_fn
        self._async_fn = async_fn

    def invoke(self, state: RunState) -> dict:
        return self._sync_fn(state)

    async def ainvoke(self, state: RunState) -> dict:
        return await self._async_fn(state)


# For backward compatibility, provide both async and sync interfaces
def build_graph():
    """
    REPLACEMENT for the original build_graph() function.

    Returns an object with .invoke/.ainvoke so existing call sites continue to work,
    but internally uses our fast async processor.
    """
    sync_fn = build_sync_processor()
    async_fn = build_async_processor()
    return _GraphLike(sync_fn, async_fn)

# Export the async version for direct use
async def process_trip_async_direct(state: RunState) -> dict:
    """Direct async interface - use this for best performance"""
    processor = build_async_processor()
    return await processor(state)