import asyncio
import time
from typing import Callable, Tuple

from langgraph.graph import StateGraph, END
from app.graph.state import RunState
from app.graph.agents import (
    destination_research,
    flight_agent,
    stay_agent,
    activities_agent,
    budget_agent,
    itinerary_synthesizer,
)

def build_graph():
    g = StateGraph(RunState)

    g.add_node("destination_research", destination_research)
    g.add_node("flight_agent", flight_agent)
    g.add_node("stay_agent", stay_agent)
    g.add_node("activities_agent", activities_agent)  # Google Places + LLM approach for diverse activities
    g.add_node("budget_agent", budget_agent)
    g.add_node("itinerary_synthesizer", itinerary_synthesizer)

    g.set_entry_point("destination_research")
    g.add_edge("destination_research", "flight_agent")
    g.add_edge("flight_agent", "stay_agent")
    g.add_edge("stay_agent", "activities_agent")
    g.add_edge("activities_agent", "budget_agent")
    g.add_edge("budget_agent", "itinerary_synthesizer")
    g.add_edge("itinerary_synthesizer", END)

    return g.compile()


# === Fast/parallel execution path (merged from fast_graph) ===

def _copy_state(state: RunState) -> RunState:
    """Deep copy a RunState to avoid shared mutable state across threads."""
    return state.model_copy(deep=True)


def _extract_new_logs(full_logs, start_index: int):
    if start_index >= len(full_logs):
        return []
    return full_logs[start_index:]


async def _run_agent_parallel(
    agent_fn: Callable[[RunState], RunState],
    base_state: RunState,
    base_log_index: int,
) -> Tuple[RunState, list]:
    """Execute a synchronous agent on a state copy inside a thread."""

    def _task():
        agent_state = _copy_state(base_state)
        updated_state = agent_fn(agent_state)
        new_logs = _extract_new_logs(updated_state.logs, base_log_index)
        return updated_state, new_logs

    return await asyncio.to_thread(_task)


class FastGraph:
    """Parallel executor: flights, stays, activities in parallel, then budget+itinerary."""

    def __init__(self) -> None:
        self._loop = None

    async def _invoke_async(self, initial_state: RunState) -> RunState:
        start = time.perf_counter()

        # Work on a deep copy to keep caller state pristine
        state = _copy_state(initial_state)

        # Destination research sequential (provides shared artifacts)
        state = destination_research(state)
        base_state = _copy_state(state)
        base_log_index = len(base_state.logs)

        # Run flight, stay, and activities in parallel threads
        flight_state, stay_state, activities_state = await asyncio.gather(
            _run_agent_parallel(flight_agent, base_state, base_log_index),
            _run_agent_parallel(stay_agent, base_state, base_log_index),
            _run_agent_parallel(activities_agent, base_state, base_log_index),
        )

        # Merge plan data
        flight_state_obj, flight_logs = flight_state
        stay_state_obj, stay_logs = stay_state
        activities_state_obj, activities_logs = activities_state

        state.plan.flights = flight_state_obj.plan.flights
        state.plan.stays = stay_state_obj.plan.stays
        state.plan.activities_catalog = activities_state_obj.plan.activities_catalog
        state.plan.itinerary = activities_state_obj.plan.itinerary

        # Merge logs in canonical order to preserve UX expectations
        state.logs.extend(flight_logs)
        state.logs.extend(stay_logs)
        state.logs.extend(activities_logs)

        # Downstream agents remain sequential (depend on upstream outputs)
        state = budget_agent(state)
        state = itinerary_synthesizer(state)
        state.done = True

        duration = time.perf_counter() - start
        state.logs.append(
            {
                "stage": "Latency",
                "message": f"Fast pipeline completed in {duration:.2f}s",
                "seconds": round(duration, 2),
                "fast_mode": True,
            }
        )

        return state

    def invoke(self, state: RunState):
        # Run as a synchronous call site by driving the coroutine to completion
        result_state = asyncio.run(self._invoke_async(state))
        return result_state.model_dump(mode="python")


def build_graph_fast() -> FastGraph:
    """Return the fast/parallel graph executor with an .invoke(state) method.

    This provides the same call surface as the compiled sequential graph while
    executing flights, stays, and activities in parallel.
    """
    return FastGraph()
