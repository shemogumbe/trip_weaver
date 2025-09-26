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
