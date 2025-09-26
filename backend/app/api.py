from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from typing import List, Optional
from pydantic import BaseModel
from app.models.trip_preferences import TravelerPrefs
from app.graph.state import RunState
from app.graph.build_graph import build_graph
from app.graph.agents import (
    destination_research,
    flight_agent,
    stay_agent,
    activities_agent,
    budget_agent,
    itinerary_synthesizer,
)
from app.main import format_plan
from app.integrations.mongo_client import log_trip_request, update_trip_result
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TripWeaver Backend API",
    description="AI-powered trip planning with enhanced Tavily integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the graph (lazy initialization for streaming reuse)
graph = build_graph()

def _format_sse(data: dict) -> str:
    """Format a dict as an SSE event line"""
    import json
    return f"data: {json.dumps(data, default=str)}\n\n"

async def _plan_trip_stream(state: RunState):
    """Generator that streams progress events while the plan is being built.
    Runs the agent pipeline step-by-step to flush updates incrementally.
    """
    import asyncio
    # Log request start (best-effort)
    req_id = log_trip_request({
        "origin": state.prefs.origin,
        "destination": state.prefs.destination,
        "start_date": str(state.prefs.start_date),
        "end_date": str(state.prefs.end_date),
        "hobbies": state.prefs.hobbies,
        "adults": state.prefs.adults,
        "budget_level": state.prefs.budget_level,
        "trip_type": state.prefs.trip_type,
        "constraints": state.prefs.constraints,
        "status": "started",
        "mode": "stream",
    })

    yield _format_sse({"stage": "start", "message": "Planning started", "request_id": req_id})

    last_len = 0

    # Phase 1: Destination research
    try:
        await asyncio.to_thread(destination_research, state)
    except Exception as e:
        yield _format_sse({"stage": "error", "message": f"Destination research failed: {e}"})
    last_len = len(state.logs)
    for log in state.logs:
        yield _format_sse({"stage": log.get("stage", "progress"), **log})

    # Phase 2: Flights
    try:
        await asyncio.to_thread(flight_agent, state)
    except Exception as e:
        yield _format_sse({"stage": "error", "message": f"Flights failed: {e}"})
    new_len = len(state.logs)
    for log in state.logs[last_len:new_len]:
        yield _format_sse({"stage": log.get("stage", "progress"), **log})
    last_len = new_len

    # Phase 3: Stays
    try:
        await asyncio.to_thread(stay_agent, state)
    except Exception as e:
        yield _format_sse({"stage": "error", "message": f"Stays failed: {e}"})
    new_len = len(state.logs)
    for log in state.logs[last_len:new_len]:
        yield _format_sse({"stage": log.get("stage", "progress"), **log})
    last_len = new_len

    # Phase 4: Activities
    try:
        await asyncio.to_thread(activities_agent, state)
    except Exception as e:
        yield _format_sse({"stage": "error", "message": f"Activities failed: {e}"})
    new_len = len(state.logs)
    for log in state.logs[last_len:new_len]:
        yield _format_sse({"stage": log.get("stage", "progress"), **log})
    last_len = new_len

    # Phase 5: Budget
    try:
        await asyncio.to_thread(budget_agent, state)
    except Exception as e:
        yield _format_sse({"stage": "error", "message": f"Budgeting failed: {e}"})
    new_len = len(state.logs)
    for log in state.logs[last_len:new_len]:
        yield _format_sse({"stage": log.get("stage", "progress"), **log})
    last_len = new_len

    # Phase 6: Itinerary synthesis
    try:
        await asyncio.to_thread(itinerary_synthesizer, state)
    except Exception as e:
        yield _format_sse({"stage": "error", "message": f"Itinerary synthesis failed: {e}"})
    new_len = len(state.logs)
    for log in state.logs[last_len:new_len]:
        yield _format_sse({"stage": log.get("stage", "progress"), **log})

    # Final payload
    try:
        final_payload = {
            "plan": format_plan(state.plan),
            "logs": state.logs,
            "success": True,
            "message": "Trip plan generated successfully",
        }
    except Exception as e:
        final_payload = {"plan": {}, "logs": state.logs, "success": False, "message": str(e)}

    # Persist final result (best-effort)
    try:
        update_trip_result(req_id, {
            "status": "success" if final_payload.get("success") else "error",
            "logs_count": len(state.logs),
            "summary": {
                "flights": len(final_payload.get("plan", {}).get("flights", [])),
                "stays": len(final_payload.get("plan", {}).get("stays", [])),
                "activities": len(final_payload.get("plan", {}).get("activities", [])),
                "itinerary_days": len(final_payload.get("plan", {}).get("itinerary", [])),
            }
        })
    except Exception:
        logger.exception("Failed to update trip result in MongoDB")

    yield _format_sse({"stage": "complete", "message": "Planning complete", "request_id": req_id})
    yield _format_sse({"stage": "result", "result": final_payload, "request_id": req_id})

class TripRequest(BaseModel):
    origin: str
    destination: str
    start_date: str  # ISO date string (YYYY-MM-DD)
    end_date: str    # ISO date string (YYYY-MM-DD)
    hobbies: List[str] = []
    adults: int = 2
    budget_level: str = "mid"  # "low", "mid", "high"
    trip_type: str = "custom"
    constraints: dict = {}

class TripResponse(BaseModel):
    plan: dict
    logs: List[dict] = []
    success: bool = True
    message: str = "Trip plan generated successfully"

@app.get("/")
def root():
    return {
        "message": "TripWeaver Backend API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "plan_trip": "/plan-trip",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy", "service": "TripWeaver Backend"}

@app.post("/plan-trip", response_model=TripResponse)
def plan_trip(request: TripRequest):
    """
    Generate a comprehensive trip plan based on traveler preferences.
    
    - **origin**: Departure location (airport code or city name)
    - **destination**: Destination location (airport code or city name)  
    - **start_date**: Trip start date (YYYY-MM-DD format)
    - **end_date**: Trip end date (YYYY-MM-DD format)
    - **hobbies**: List of interests/activities (e.g., ["night life", "fine dining", "golf"])
    - **adults**: Number of adults (default: 2)
    - **budget_level**: Budget level - "low", "mid", or "high" (default: "mid")
    - **trip_type**: Type of trip (default: "custom")
    - **constraints**: Additional constraints as key-value pairs
    """
    try:
        # Parse dates
        try:
            start_date = date.fromisoformat(request.start_date)
            end_date = date.fromisoformat(request.end_date)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
        
        # Validate date range
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="End date must be after start date")
        
        # Create preferences object
        prefs = TravelerPrefs(
            origin=request.origin,
            destination=request.destination,
            start_date=start_date,
            end_date=end_date,
            adults=request.adults,
            budget_level=request.budget_level,
            hobbies=request.hobbies,
            trip_type=request.trip_type,
            constraints=request.constraints
        )
        
        logger.info(f"Generating trip plan: {prefs.origin} -> {prefs.destination} ({prefs.start_date} to {prefs.end_date})")
        
        # Log request start (best-effort)
        req_id = log_trip_request({
            "origin": prefs.origin,
            "destination": prefs.destination,
            "start_date": str(prefs.start_date),
            "end_date": str(prefs.end_date),
            "hobbies": prefs.hobbies,
            "adults": prefs.adults,
            "budget_level": prefs.budget_level,
            "trip_type": prefs.trip_type,
            "constraints": prefs.constraints,
            "status": "started",
            "mode": "sync",
        })

        # Run the trip planning graph
        state = RunState(prefs=prefs)
        result = graph.invoke(state)
        
        # Format the response
        plan = result["plan"]
        formatted_plan = format_plan(plan)
        
        response = TripResponse(
            plan=formatted_plan,
            logs=result.get("logs", []),
            success=True,
            message=f"Trip plan generated for {prefs.origin} to {prefs.destination}"
        )
        
        logger.info(f"Trip plan generated successfully with {len(formatted_plan.get('flights', []))} flights, {len(formatted_plan.get('stays', []))} stays, and {len(formatted_plan.get('activities', []))} activity days")
        
        try:
            update_trip_result(req_id, {
                "status": "success",
                "logs_count": len(result.get("logs", [])),
                "summary": {
                    "flights": len(formatted_plan.get("flights", [])),
                    "stays": len(formatted_plan.get("stays", [])),
                    "activities": len(formatted_plan.get("activities", [])),
                    "itinerary_days": len(formatted_plan.get("itinerary", [])),
                }
            })
        except Exception:
            logger.exception("Failed to update trip result in MongoDB")

        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating trip plan: {e}")
        try:
            update_trip_result(locals().get("req_id", None), {"status": "error", "error": str(e)})
        except Exception:
            logger.exception("Failed to update error in MongoDB")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/plan-trip/stream")
async def plan_trip_stream(request: TripRequest):
    """
    Streaming (SSE) endpoint: emits incremental progress events while planning.
    Events include stages like Flights Found, Flights Refined, Stays Found, Activities Found, etc.
    """
    from datetime import date
    try:
        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="End date must be after start date")

        prefs = TravelerPrefs(
            origin=request.origin,
            destination=request.destination,
            start_date=start_date,
            end_date=end_date,
            adults=request.adults,
            budget_level=request.budget_level,
            hobbies=request.hobbies,
            trip_type=request.trip_type,
            constraints=request.constraints,
        )
        state = RunState(prefs=prefs)

        return StreamingResponse(
            _plan_trip_stream(state),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting streaming plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plan-trip/stream")
async def plan_trip_stream_get(
    origin: str,
    destination: str,
    start_date: str,
    end_date: str,
    adults: int = 2,
    budget_level: str = "mid",
    trip_type: str = "custom",
    hobbies: Optional[str] = None,
    constraints: Optional[str] = None,
):
    """
    GET variant for SSE streaming to support EventSource (which only uses GET).
    Complex fields (hobbies, constraints) are accepted as JSON strings in query params.
    """
    try:
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
        if sd >= ed:
            raise HTTPException(status_code=400, detail="End date must be after start date")

        # Parse optional JSON fields
        parsed_hobbies: List[str] = []
        if hobbies:
            try:
                parsed = json.loads(hobbies)
                if isinstance(parsed, list):
                    parsed_hobbies = [str(x) for x in parsed]
                else:
                    parsed_hobbies = []
            except Exception:
                # fallback: comma-separated
                parsed_hobbies = [h.strip() for h in hobbies.split(',') if h.strip()]

        parsed_constraints: dict = {}
        if constraints:
            try:
                parsed = json.loads(constraints)
                parsed_constraints = parsed if isinstance(parsed, dict) else {}
            except Exception:
                parsed_constraints = {}

        prefs = TravelerPrefs(
            origin=origin,
            destination=destination,
            start_date=sd,
            end_date=ed,
            adults=adults,
            budget_level=budget_level,
            hobbies=parsed_hobbies,
            trip_type=trip_type,
            constraints=parsed_constraints,
        )
        state = RunState(prefs=prefs)
        return StreamingResponse(
            _plan_trip_stream(state),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting streaming plan (GET): {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Legacy endpoint for backward compatibility
@app.post("/plan")
def plan_legacy(prefs: TravelerPrefs):
    """
    Legacy endpoint - use /plan-trip for new integrations
    """
    try:
        state = RunState(prefs=prefs)
        result = graph.invoke(state)
        return {"plan": result.plan.dict()}
    except Exception as e:
        logger.error(f"Error in legacy plan endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
