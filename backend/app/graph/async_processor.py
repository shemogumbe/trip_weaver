"""
Async processor that preserves rich agent logic while adding parallelism.

We keep agents synchronous (rich Tavily + LLM flows) and run them in parallel
via asyncio.to_thread on separate child states to avoid write conflicts.
Then we merge their outputs back into a single master state.
"""

from __future__ import annotations

import asyncio
from typing import Dict

from app.graph.state import RunState
from app.graph.agents import (
    destination_research,
    flight_agent,
    stay_agent,
    optimized_activities_agent_with_openai as activities_agent,
    budget_agent,
    itinerary_synthesizer,
)


def _clone_for_agent(state: RunState) -> RunState:
    """Create a lightweight child state for an agent to write into safely."""
    return RunState(prefs=state.prefs)


async def process_trip_async(state: RunState) -> RunState:
    """
    Run destination research first, then execute flights, stays, and activities
    in parallel, preserving each agent's full richness. Finally compute budget
    and synthesize itinerary.
    """
    # Phase 1: destination research (sequential prerequisite)
    destination_research(state)

    # Phase 2: run three agents in parallel on cloned states
    flight_state = _clone_for_agent(state)
    stay_state = _clone_for_agent(state)
    act_state = _clone_for_agent(state)

    async def run_flights():
        await asyncio.to_thread(flight_agent, flight_state)

    async def run_stays():
        await asyncio.to_thread(stay_agent, stay_state)

    async def run_activities():
        await asyncio.to_thread(activities_agent, act_state)

    await asyncio.gather(run_flights(), run_stays(), run_activities())

    # Phase 3: merge results back into master state
    state.plan.flights = flight_state.plan.flights
    state.plan.stays = stay_state.plan.stays
    state.plan.activities_catalog = act_state.plan.activities_catalog
    state.plan.itinerary = act_state.plan.itinerary

    # Carry over any artifacts collected by the agents
    state.artifacts.update(flight_state.artifacts or {})
    state.artifacts.update(stay_state.artifacts or {})
    state.artifacts.update(act_state.artifacts or {})

    # Phase 4: budget and final itinerary synthesis (sequential)
    budget_agent(state)
    itinerary_synthesizer(state)

    return state


def build_async_processor():
    """Return an async function compatible with the graph-style interface."""

    async def _process(state: RunState) -> Dict:
        result_state = await process_trip_async(state)
        return {
            "plan": result_state.plan,
            "artifacts": result_state.artifacts,
            "logs": result_state.logs,
            "prefs": result_state.prefs,
        }

    return _process


def build_sync_processor():
    """Synchronous wrapper around the async processor."""
    async_fn = build_async_processor()

    def _sync(state: RunState) -> Dict:
        return asyncio.run(async_fn(state))

    return _sync


class _GraphLike:
    """Mimic LangGraph's .invoke/.ainvoke interface for easy swapping."""

    def __init__(self, sync_fn, async_fn):
        self._sync_fn = sync_fn
        self._async_fn = async_fn

    def invoke(self, state: RunState) -> Dict:
        return self._sync_fn(state)

    async def ainvoke(self, state: RunState) -> Dict:
        return await self._async_fn(state)


def build_graph():
    """
    Provide a graph-like wrapper using the async processor. This does not
    modify the existing LangGraph-based builder; import this module directly
    where async parallelism is desired.
    """
    sync_fn = build_sync_processor()
    async_fn = build_async_processor()
    return _GraphLike(sync_fn, async_fn)


async def process_trip_async_direct(state: RunState) -> Dict:
    """Direct async entrypoint returning the same dict shape used by API."""
    processor = build_async_processor()
    return await processor(state)
