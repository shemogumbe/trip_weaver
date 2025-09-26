<<<<<<< HEAD
"""Utility script to compare sequential vs fast graph latency."""

import os
import time
from datetime import date
from typing import Any, Dict

from app.models.trip_preferences import TravelerPrefs
from app.graph.state import RunState
from app.graph.build_graph import build_graph


def _extract_plan(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return result.get("plan", {})
    if hasattr(result, "plan"):
        plan = getattr(result, "plan")
        if hasattr(plan, "model_dump"):
            return plan.model_dump(mode="python")
        if hasattr(plan, "dict"):
            return plan.dict()
        return plan
    raise ValueError("Unexpected result type from graph.invoke")


def _extract_logs(result: Any):
    if isinstance(result, dict):
        return result.get("logs", [])
    if hasattr(result, "logs"):
        logs = getattr(result, "logs")
        if hasattr(logs, "model_dump"):
            return logs.model_dump(mode="python")
        if isinstance(logs, list):
            return list(logs)
        return list(logs)
    return []


def run_trial(use_fast: bool) -> None:
    label = "fast" if use_fast else "sequential"
    graph = build_graph(use_fast=use_fast)

    prefs = TravelerPrefs(
        origin="NBO",
        destination="DXB",
        start_date=date(2025, 1, 10),
        end_date=date(2025, 1, 16),
        hobbies=["fine dining", "golf", "night life"],
        adults=2,
        budget_level="mid",
        trip_type="vacation",
        constraints={},
    )

    state = RunState(prefs=prefs)

    print(f"Running {label} graph...")
    start = time.perf_counter()
    result = graph.invoke(state)
    duration = time.perf_counter() - start

    plan = _extract_plan(result)
    logs = _extract_logs(result)

    print(
        f"{label.capitalize()} runtime: {duration:.2f}s | "
        f"flights: {len(plan.get('flights', []))}, "
        f"stays: {len(plan.get('stays', []))}, "
        f"activity days: {len(plan.get('itinerary', []))}, "
        f"logs: {len(logs)}"
    )
    if logs and logs[-1].get("stage") == "Latency":
        print(f"  -> Reported latency log: {logs[-1]}")
    print()


if __name__ == "__main__":
    run_trial(use_fast=False)
    run_trial(use_fast=True)
=======
#!/usr/bin/env python3
"""
Latency Measurement Script for TripWeaver

This script measures the actual current latency of each agent and the total pipeline
to establish a baseline before optimizations.
"""

import time
import asyncio
import logging
from datetime import date
from app.graph.state import RunState
from app.models.trip_preferences import TravelerPrefs
from app.graph.build_graph import build_graph

# Suppress non-critical logs for cleaner timing output
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

def measure_current_latency():
    """
    Measure current latency of the complete TripWeaver pipeline
    """
    print("🕒 TripWeaver Current Latency Measurement")
    print("=" * 60)
    
    # Create test preferences (realistic trip)
    prefs = TravelerPrefs(
        origin="NBO",
        destination="Dubai", 
        start_date=date(2025, 11, 10),
        end_date=date(2025, 11, 16),
        hobbies=["golf", "fine dining", "nightlife"],
        adults=2,
        budget_level="mid",
        trip_type="honeymoon",
        constraints={}
    )
    
    initial_state = RunState(prefs=prefs)
    
    print(f"📍 Test Trip Configuration:")
    print(f"   Route: {prefs.origin} → {prefs.destination}")
    print(f"   Duration: {prefs.start_date} to {prefs.end_date} ({(prefs.end_date - prefs.start_date).days + 1} days)")
    print(f"   Hobbies: {', '.join(prefs.hobbies)}")
    print(f"   Adults: {prefs.adults}")
    print(f"   Budget: {prefs.budget_level}")
    print()
    
    # Build the graph
    graph = build_graph()
    
    # Overall timing
    total_start_time = time.time()
    
    try:
        print("🚀 Starting TripWeaver pipeline execution...")
        print()
        
        # Execute the complete graph
        result = graph.invoke(initial_state)
        
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        print("✅ Pipeline execution completed!")
        print()
        
        # Results summary
        print("📊 RESULTS SUMMARY:")
        print("-" * 40)
        print(f"Flights found: {len(result.plan.flights)}")
        print(f"Stays found: {len(result.plan.stays)}")
        print(f"Activities catalog: {len(result.plan.activities_catalog)}")
        print(f"Activity days: {len(result.plan.itinerary)}")
        print(f"Sources collected: {len(result.plan.sources)}")
        print()
        
        # Timing results
        print("⏱️  LATENCY MEASUREMENT:")
        print("-" * 40)
        print(f"🕒 TOTAL LATENCY: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        
        # Categorize performance
        if total_duration < 30:
            status = "🟢 EXCELLENT"
        elif total_duration < 60:
            status = "🟡 GOOD" 
        elif total_duration < 120:
            status = "🟠 ACCEPTABLE"
        elif total_duration < 240:
            status = "🔴 SLOW"
        else:
            status = "🚨 CRITICAL"
            
        print(f"Performance: {status}")
        print()
        
        # Performance breakdown estimate based on typical patterns
        estimated_breakdown = {
            "Destination Research": total_duration * 0.25,
            "Flight Search": total_duration * 0.20, 
            "Stay Search": total_duration * 0.22,
            "Activities Generation": total_duration * 0.20,
            "Budget & Itinerary": total_duration * 0.13
        }
        
        print("📈 ESTIMATED AGENT BREAKDOWN:")
        print("-" * 40)
        for agent, estimated_time in estimated_breakdown.items():
            print(f"{agent:<20}: ~{estimated_time:.1f}s")
        print()
        
        # Optimization potential
        optimization_potential = max(0, total_duration - 40)
        if optimization_potential > 0:
            print("🚀 OPTIMIZATION ANALYSIS:")
            print("-" * 40)
            print(f"Current latency: {total_duration:.1f}s")
            print(f"Target latency: 40s")
            print(f"Improvement needed: {optimization_potential:.1f}s ({optimization_potential/total_duration*100:.1f}%)")
            print()
            
            # Specific recommendations
            print("💡 OPTIMIZATION OPPORTUNITIES:")
            if total_duration > 120:
                print("   🔥 HIGH IMPACT:")
                print("      • Implement async parallel execution")
                print("      • Reduce API calls with smart batching")
                print("      • Skip optional t_crawl operations")
            if total_duration > 60:
                print("   🟡 MEDIUM IMPACT:")
                print("      • Use basic search depth instead of advanced")
                print("      • Optimize LLM call parameters")
                print("      • Implement result caching")
            if total_duration > 40:
                print("   🟢 LOW IMPACT:")
                print("      • Fine-tune timeout settings")
                print("      • Optimize data processing")
        else:
            print("🎉 Current performance is already within target range!")
        
        return {
            "total_latency": total_duration,
            "flights": len(result.plan.flights),
            "stays": len(result.plan.stays), 
            "activities": len(result.plan.activities_catalog),
            "sources": len(result.plan.sources),
            "status": status
        }
        
    except Exception as e:
        total_duration = time.time() - total_start_time
        print(f"❌ Pipeline execution failed after {total_duration:.1f}s")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "duration": total_duration}

def measure_individual_agents():
    """
    Measure individual agent performance (more detailed analysis)
    """
    print("\n" + "="*60)
    print("🔬 INDIVIDUAL AGENT LATENCY MEASUREMENT")
    print("="*60)
    
    # Import individual agents
    from app.graph.agents import (
        destination_research, 
        flight_agent, 
        stay_agent, 
        activities_agent, 
        budget_agent, 
        itinerary_synthesizer
    )
    
    # Create test state
    prefs = TravelerPrefs(
        origin="NBO",
        destination="Dubai", 
        start_date=date(2025, 11, 10),
        end_date=date(2025, 11, 16),
        hobbies=["golf", "fine dining"],  # Reduced for faster testing
        adults=2,
        budget_level="mid",
        trip_type="honeymoon"
    )
    
    state = RunState(prefs=prefs)
    
    agents = [
        ("Destination Research", destination_research),
        ("Flight Agent", flight_agent),
        ("Stay Agent", stay_agent), 
        ("Activities Agent", activities_agent),
        ("Budget Agent", budget_agent),
        ("Itinerary Synthesizer", itinerary_synthesizer)
    ]
    
    individual_times = {}
    cumulative_state = state
    
    for agent_name, agent_func in agents:
        print(f"\n🔍 Testing {agent_name}...")
        
        start_time = time.time()
        try:
            cumulative_state = agent_func(cumulative_state)
            duration = time.time() - start_time
            individual_times[agent_name] = duration
            
            print(f"✅ {agent_name}: {duration:.1f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            individual_times[agent_name] = duration
            print(f"❌ {agent_name}: {duration:.1f}s (failed: {e})")
    
    print(f"\n📊 INDIVIDUAL AGENT TIMING SUMMARY:")
    print("-" * 50)
    total_individual = 0
    for agent_name, duration in individual_times.items():
        print(f"{agent_name:<20}: {duration:>6.1f}s")
        total_individual += duration
    
    print("-" * 50)
    print(f"{'TOTAL':<20}: {total_individual:>6.1f}s")
    
    return individual_times

if __name__ == "__main__":
    try:
        # Measure overall latency
        results = measure_current_latency()
        
        # Optionally measure individual agents for detailed analysis
        print("\n" + "?"*60)
        user_input = input("🔬 Run detailed individual agent analysis? (y/N): ").lower().strip()
        if user_input in ['y', 'yes']:
            individual_results = measure_individual_agents()
        
        print(f"\n🎯 MEASUREMENT COMPLETE!")
        if 'total_latency' in results:
            print(f"Current system latency: {results['total_latency']:.1f} seconds")
        
    except KeyboardInterrupt:
        print("\n⏹️  Measurement interrupted by user")
    except Exception as e:
        print(f"\n❌ Measurement failed: {e}")
        import traceback
        traceback.print_exc()
>>>>>>> 0d79b3c (stream responses for user engagement)
