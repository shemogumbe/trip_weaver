# TripWeaver Backend - AI Coding Agent Instructions

## Architecture Overview

**LangGraph-Based AI Trip Planner**: This is a FastAPI backend that orchestrates multiple AI agents through a directed graph to generate comprehensive travel plans. The core pipeline flows through: Destination Research → Flight Search → Accommodation Search → Activity Generation → Budget Analysis → Itinerary Synthesis.

### Key Components

- **`app/api.py`**: FastAPI endpoints with `/plan-trip` as the main interface and `/plan` for legacy support
- **`app/graph/build_graph.py`**: LangGraph pipeline definition connecting agents sequentially  
- **`app/graph/agents.py`**: Six specialized agents handling different aspects of trip planning
- **`app/graph/state.py`**: Shared state (`RunState`) passed between agents containing `prefs` (user input) and `plan` (accumulated results)
- **`app/models/entities.py`**: Pydantic models defining structured data: `FlightOption`, `StayOption`, `Activity`, `DayPlan`
- **`app/integrations/`**: External API clients for Tavily (search) and OpenAI (LLM processing)

## Critical Workflow Patterns

### Agent Architecture
Agents are pure functions taking `RunState` and returning modified `RunState`. Each agent enriches `state.plan` with its domain data:
```python
def my_agent(state: RunState) -> RunState:
    # Process state.prefs (user input)
    # Update state.plan.flights/stays/activities_catalog  
    # Add to state.logs for debugging
    return state
```

### Cost Optimization Strategy 
**ULTRA-OPTIMIZED pattern**: The activities agent (`optimized_activities_agent_with_openai`) replaces 22 Tavily API calls with 1 OpenAI call, achieving 95% cost reduction. 

**ENHANCED ACTIVITIES OPTION**: For better activity diversity, `practical_enhanced_activities_agent` in `practical_enhanced_activities.py` provides 2-3x more activities with geographic refinement and hobby-specific searches. Trade-off: ~15-30 seconds vs 5-8 seconds, but significantly better coverage. Use the test script `test_enhanced_activities.py` to compare approaches.

### LLM Refinement Pattern
Raw search data gets processed through specialized refinement functions in `app/graph/utils/postprocess/refine_*_with_llm.py`. These use structured OpenAI prompts with JSON schema to convert messy web data into clean Pydantic models. Always use `response_format={"type": "json_object"}` for structured generation.

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Required .env variables
TAVILY_API_KEY=your_tavily_key
OPENAI_API_KEY=your_openai_key
```

### Running & Testing
```bash
# Start development server (auto-reload enabled)
python run_server.py

# Test all endpoints
python test_api.py

# Interactive API docs
http://localhost:8000/docs
```

## Critical Implementation Notes

### Date Handling
- Use `date.fromisoformat()` for string-to-date conversion
- API expects ISO format ("2025-11-10")
- Activity distribution excludes arrival/departure days for trips >2 days

### Price Validation
Always validate prices through `validate_price_reasonableness()` in `app/graph/utils/general_utils.py`. This prevents LLMs from extracting years (2025) or discount percentages as prices.

### Error Handling in Integrations
Tavily calls may fail; always provide fallback behavior:
```python
search_result = t_search(query)
results = search_result.get("results", [])  # Safe extraction
```

### State Management
- `state.plan` accumulates all trip components across agents
- `state.artifacts` stores intermediate data for debugging
- `state.logs` tracks processing statistics for each stage

## Project-Specific Conventions

### Response Formatting
Use `format_plan()` in `main.py` to convert internal Pydantic models to API-friendly dictionaries. This prunes unnecessary fields and handles the activities → itinerary transformation.

### Booking Links Sanitization
When processing LLM outputs, always sanitize booking_links which can be strings, lists, or nested dicts from GPT responses. See `sanitize_flight_dict()` pattern in refinement modules.

### Activity Scheduling
Activities use a three-slot system (morning/afternoon/evening) with duration-based conflict detection in `ensure_time_feasible()`. Long activities (>8 hours) cancel other activities for that day.

## Integration Points

- **Tavily Client**: Travel-specific search with curated domain filtering (`TRAVEL_DOMAINS` in `tavily_client.py`)
- **OpenAI Client**: Structured data extraction with JSON mode for consistent parsing
- **FastAPI**: CORS-enabled with automatic OpenAPI documentation generation

When modifying agents, maintain the sequential flow and ensure each agent populates its designated `state.plan` fields. The system's cost efficiency depends on minimal API calls per agent.