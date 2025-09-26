#!/usr/bin/env python3
"""
Test script to demonstrate parallel execution timing without hitting external APIs.
Shows the improvement from sequential to parallel agent execution.
"""

import time
import logging
from datetime import date
from typing import Dict, Any

# Mock timing data based on real-world agent execution times
MOCK_TIMINGS = {
    "destination_research": 18.5,  # seconds
    "flight_agent": 45.2,
    "stay_agent": 52.1, 
    "activities_agent": 38.7,
    "budget_agent": 2.1,
    "itinerary_synthesizer": 6.8
}

def simulate_agent_execution(agent_name: str, parallel: bool = False) -> Dict[str, Any]:
    """Simulate agent execution with realistic timing"""
    start_time = time.time()
    duration = MOCK_TIMINGS[agent_name]
    
    # Simulate some CPU work (reduced duration for demo)
    time.sleep(duration / 10)  # Scale down for demo (4.5s instead of 45s)
    
    end_time = time.time()
    actual_duration = end_time - start_time
    
    mode = "PARALLEL" if parallel else "SEQUENTIAL" 
    logging.info(f"✅ {agent_name} completed in {actual_duration:.2f}s ({mode} mode)")
    
    return {
        "agent": agent_name,
        "duration": actual_duration,
        "mode": mode
    }

def test_sequential_execution():
    """Original sequential execution pattern"""
    logging.info("🐌 Testing SEQUENTIAL execution (original)...")
    
    total_start = time.time()
    results = []
    
    # Sequential execution - each waits for the previous
    results.append(simulate_agent_execution("destination_research"))
    results.append(simulate_agent_execution("flight_agent"))
    results.append(simulate_agent_execution("stay_agent"))
    results.append(simulate_agent_execution("activities_agent"))
    results.append(simulate_agent_execution("budget_agent"))
    results.append(simulate_agent_execution("itinerary_synthesizer"))
    
    total_time = time.time() - total_start
    logging.info(f"📊 SEQUENTIAL total time: {total_time:.2f}s")
    
    return total_time

def test_parallel_execution():
    """New parallel execution pattern"""
    logging.info("🚀 Testing PARALLEL execution (optimized)...")
    
    total_start = time.time()
    
    # Phase 1: Destination research (must be first)
    simulate_agent_execution("destination_research", parallel=True)
    
    # Phase 2: Parallel data collection - simulate with threading
    import threading
    
    parallel_start = time.time()
    threads = []
    results = []
    
    def run_agent(agent_name):
        result = simulate_agent_execution(agent_name, parallel=True)
        results.append(result)
    
    # Start all three agents in parallel
    for agent in ["flight_agent", "stay_agent", "activities_agent"]:
        thread = threading.Thread(target=run_agent, args=(agent,))
        thread.start()
        threads.append(thread)
    
    # Wait for all parallel agents to complete
    for thread in threads:
        thread.join()
    
    parallel_time = time.time() - parallel_start
    logging.info(f"⚡ Parallel phase completed in {parallel_time:.2f}s")
    
    # Phase 3: Sequential completion
    simulate_agent_execution("budget_agent", parallel=True)
    simulate_agent_execution("itinerary_synthesizer", parallel=True)
    
    total_time = time.time() - total_start
    logging.info(f"📊 PARALLEL total time: {total_time:.2f}s")
    
    return total_time

def main():
    """Run both tests and compare results"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print("="*60)
    print("🧪 TRIPWEAVER PARALLEL EXECUTION TEST")
    print("="*60)
    
    # Test sequential execution
    sequential_time = test_sequential_execution()
    
    print("\n" + "-"*60 + "\n")
    
    # Test parallel execution  
    parallel_time = test_parallel_execution()
    
    # Calculate improvement
    improvement = ((sequential_time - parallel_time) / sequential_time) * 100
    speedup = sequential_time / parallel_time
    
    print("\n" + "="*60)
    print("📈 PERFORMANCE COMPARISON")
    print("="*60)
    print(f"Sequential Time:  {sequential_time:.2f}s")
    print(f"Parallel Time:    {parallel_time:.2f}s")
    print(f"Improvement:      {improvement:.1f}% faster")
    print(f"Speedup Factor:   {speedup:.2f}x")
    print("="*60)
    
    if improvement > 50:
        print("🎉 SUCCESS: Parallel execution significantly reduces response time!")
    else:
        print("⚠️  WARNING: Parallel execution improvement is less than expected")
    
    # Scaled estimates for real execution
    print(f"\n🔮 REAL-WORLD ESTIMATES:")
    print(f"Sequential (scaled): {sequential_time * 10:.0f}s ({sequential_time * 10 / 60:.1f} minutes)")
    print(f"Parallel (scaled):   {parallel_time * 10:.0f}s ({parallel_time * 10 / 60:.1f} minutes)")

if __name__ == "__main__":
    main()