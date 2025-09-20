from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from typing import List, Optional
from pydantic import BaseModel
from app.models.trip_preferences import TravelerPrefs
from app.graph.state import RunState
from app.graph.build_graph import build_graph
from app.main import format_plan
import logging

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

# Initialize the graph
graph = build_graph()

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
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating trip plan: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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
