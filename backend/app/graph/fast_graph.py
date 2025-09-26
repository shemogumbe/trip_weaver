<<<<<<< HEAD
import asyncio
import os
import time
from typing import Callable, Tuple

from app.graph.state import RunState
from app.graph.agents import (
    destination_research,
    flight_agent,
    stay_agent,
    activities_agent,
    budget_agent,
    itinerary_synthesizer,
)


def _copy_state(state: RunState) -> RunState:
    """Helper to deep copy a RunState to avoid shared mutable state."""
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
    """Drop-in replacement for the LangGraph compile with parallel agent execution."""

    def __init__(self) -> None:
        self._loop = None

    async def _invoke_async(self, initial_state: RunState) -> RunState:
        start = time.perf_counter()

        # Always work on a deep copy to keep caller state pristine
        state = _copy_state(initial_state)

        # Destination research stays sequential (provides shared artifacts)
        state = destination_research(state)
        base_state = _copy_state(state)
        base_log_index = len(base_state.logs)

        # Kick off flight, stay, and activity agents in parallel threads
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

        # Merge logs in the canonical order to preserve UX expectations
        state.logs.extend(flight_logs)
        state.logs.extend(stay_logs)
        state.logs.extend(activities_logs)

        # Downstream agents remain sequential (they depend on upstream outputs)
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
        if self._loop and self._loop.is_running():
            # Should not happen under current sync FastAPI routes; fallback to to_thread
            return asyncio.run_coroutine_threadsafe(
                self._invoke_async(state), self._loop
            ).result().model_dump(mode="python")

        result_state = asyncio.run(self._invoke_async(state))
        return result_state.model_dump(mode="python")


def fast_graph_enabled_from_env(default: bool = False) -> bool:
    flag = os.getenv("FAST_GRAPH_ENABLED")
    if flag is None:
        return default
    return flag.lower() in {"1", "true", "yes", "on"}
=======
"""
Fast Graph Builder - Optimized execution flow for 40-second trip planning

Key optimizations:
1. Async/await for parallel execution
2. Independent agents run in parallel  
3. Reduced API calls per agent
4. Smart batching and caching
"""

import asyncio
from langgraph.graph import StateGraph, END
from app.graph.state import RunState
from app.graph.fast_agents import (
    fast_destination_research, 
    fast_flight_agent, 
    fast_stay_agent, 
    fast_activities_agent
)
from app.graph.agents import budget_agent, itinerary_synthesizer

async def fast_trip_planning_flow(state: RunState) -> RunState:
    """
    Optimized trip planning flow with parallel execution
    
    Original Flow (Sequential): ~240+ seconds
    destination → flight → stay → activities → budget → itinerary
    
    Optimized Flow (Parallel): ~40-50 seconds  
    destination → (flight + stay + activities) → budget → itinerary
    """
    
    try:
        # Phase 1: Destination research (required first - 6 API calls, ~8 sec)
        print("🔍 Phase 1: Destination research...")
        start_time = asyncio.get_event_loop().time()
        
        state = await fast_destination_research(state)
        phase1_time = asyncio.get_event_loop().time() - start_time
        print(f"✅ Destination research completed in {phase1_time:.1f}s")
        
        # Phase 2: Parallel data gathering (flight + stay + activities in parallel - ~15 sec)
        print("🚀 Phase 2: Parallel data gathering (flights, stays, activities)...")
        phase2_start = asyncio.get_event_loop().time()
        
        # Run independent agents in parallel
        flight_task = fast_flight_agent(state.copy())
        stay_task = fast_stay_agent(state.copy()) 
        activities_task = fast_activities_agent(state.copy())
        
        # Execute all three in parallel
        flight_result, stay_result, activities_result = await asyncio.gather(
            flight_task,
            stay_task, 
            activities_task,
            return_exceptions=True
        )
        
        # Merge results back to main state
        if not isinstance(flight_result, Exception):
            state.plan.flights = flight_result.plan.flights
        if not isinstance(stay_result, Exception):
            state.plan.stays = stay_result.plan.stays  
        if not isinstance(activities_result, Exception):
            state.plan.activities_catalog = activities_result.plan.activities_catalog
            state.plan.itinerary = activities_result.plan.itinerary
        
        phase2_time = asyncio.get_event_loop().time() - phase2_start
        print(f"✅ Parallel gathering completed in {phase2_time:.1f}s")
        
        # Phase 3: Budget and itinerary synthesis (sequential - ~5 sec)
        print("💰 Phase 3: Budget calculation and itinerary synthesis...")
        phase3_start = asyncio.get_event_loop().time()
        
        # These need to be sequential as they depend on all previous data
        state = await asyncio.to_thread(budget_agent, state)
        state = await asyncio.to_thread(itinerary_synthesizer, state)
        
        phase3_time = asyncio.get_event_loop().time() - phase3_start  
        print(f"✅ Budget and itinerary completed in {phase3_time:.1f}s")
        
        # Total time
        total_time = phase1_time + phase2_time + phase3_time
        print(f"🎉 FAST PLANNING COMPLETE: {total_time:.1f}s total")
        print(f"   • Phase 1 (Research): {phase1_time:.1f}s")
        print(f"   • Phase 2 (Parallel): {phase2_time:.1f}s")  
        print(f"   • Phase 3 (Synthesis): {phase3_time:.1f}s")
        
        return state
        
    except Exception as e:
        print(f"❌ Fast planning failed: {e}")
        import traceback
        traceback.print_exc()
        return state

def build_fast_graph():
    """
    Build the fast execution graph
    Note: This is a demonstration - actual LangGraph integration would need more work
    """
    g = StateGraph(RunState)
    
    # For now, we'll use a single node that handles the optimized flow
    async def fast_planning_node(state: RunState) -> RunState:
        return await fast_trip_planning_flow(state)
    
    g.add_node("fast_planning", fast_planning_node)
    g.set_entry_point("fast_planning") 
    g.add_edge("fast_planning", END)
    
    return g.compile()

# Alternative: Hybrid approach for gradual migration
def build_hybrid_graph():
    """
    Hybrid approach: Use fast agents in existing graph structure
    This allows gradual migration while maintaining compatibility
    """
    g = StateGraph(RunState)
    
    # Use fast agents instead of original ones
    g.add_node("destination_research", fast_destination_research)
    g.add_node("flight_agent", fast_flight_agent)
    g.add_node("stay_agent", fast_stay_agent)
    g.add_node("activities_agent", fast_activities_agent)
    g.add_node("budget_agent", budget_agent)  # Keep original
    g.add_node("itinerary_synthesizer", itinerary_synthesizer)  # Keep original
    
    # Keep sequential structure for now (easier migration)
    g.set_entry_point("destination_research")
    g.add_edge("destination_research", "flight_agent")
    g.add_edge("flight_agent", "stay_agent") 
    g.add_edge("stay_agent", "activities_agent")
    g.add_edge("activities_agent", "budget_agent")
    g.add_edge("budget_agent", "itinerary_synthesizer")
    g.add_edge("itinerary_synthesizer", END)
    
    return g.compile()

if __name__ == "__main__":
    # Test the fast planning flow
    from app.models.trip_preferences import TravelerPrefs
    from datetime import date
    
    prefs = TravelerPrefs(
        origin="NBO",
        destination="Dubai", 
        start_date=date(2025, 11, 10),
        end_date=date(2025, 11, 16),
        hobbies=["golf", "fine dining"],
        adults=2,
        budget_level="mid",
        trip_type="honeymoon"
    )
    
    state = RunState(prefs=prefs)
    
    async def test_fast_planning():
        result = await fast_trip_planning_flow(state)
        print(f"🎯 Generated {len(result.plan.flights)} flights")
        print(f"🏨 Generated {len(result.plan.stays)} stays") 
        print(f"🎪 Generated {len(result.plan.activities_catalog)} activities")
    
    # asyncio.run(test_fast_planning())
>>>>>>> 0d79b3c (stream responses for user engagement)
