# TripWeaver Backend API

AI-powered trip planning with enhanced Tavily integration for accurate travel data.

## Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variables
Create a `.env` file in the backend directory:
```bash
TAVILY_API_KEY=your_tavily_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
# Runtime toggles (optional)
# SPEED_MODE=1  # default: 1 (minimize Tavily calls); set 0 for richer results
# AGENT_TIMEOUT_SECONDS=20  # default: 20 (40 when SPEED_MODE=0)
```

### 3. Start the Server
```bash
python run_server.py
```

The API will be available at: http://localhost:8000

### 4. Test the API
```bash
# Run the test script
python test_api.py

# Or visit the interactive docs
open http://localhost:8000/docs
```

## API Endpoints

### `POST /plan-trip` (Recommended)
Generate a comprehensive trip plan.

**Request Body:**
```json
{
  "origin": "NBO",
  "destination": "Dubai",
  "start_date": "2025-11-10",
  "end_date": "2025-11-16",
  "hobbies": ["night life", "fine dining", "golf"],
  "adults": 2,
  "budget_level": "mid",
  "trip_type": "honeymoon",
  "constraints": {}
}
```

**Response:**
```json
{
  "plan": {
    "flights": [...],
    "stays": [...],
    "activities": [...]
  },
  "logs": [...],
  "success": true,
  "message": "Trip plan generated successfully"
}
```

### `GET /health`
Check API health status.

### `GET /`
Get API information and available endpoints.

### `POST /plan` (Legacy)
Legacy endpoint for backward compatibility.

## Features

### 🚀 OpenAI-Based Activity Generation (NEW)
**42% Cost Reduction with Better Activity Distribution**

- **Replaces 22 Tavily calls** with 1 OpenAI call for activity generation
- **Smart day planning:** No activities on arrival/departure days
- **Even distribution:** Activities spread across available days (not cramped in early days)
- **Comprehensive generation:** Activities based on destination, interests, budget level
- **Same response format:** No frontend breaking changes

**Cost Impact:**
- Activities agent: 22 Tavily calls → 1 Tavily + 1 OpenAI call (95% reduction)
- Overall trip cost: $0.406 → $0.244 per trip (40% savings)
- Trips per 1000 Tavily credits: 20 → 33 trips

**Activity Distribution Example (7-day trip):**
```
Day 1: Arrival - NO ACTIVITIES
Days 2-6: Morning/afternoon/evening activities 
Day 7: Departure - NO ACTIVITIES
```

###  Enhanced Flight Data
- Multi-query search with extraction
- Airline-specific crawling
- Price validation (avoids year/discount confusion)
- Currency detection and validation

###  Smart Hotel Recommendations
- Booking site crawling for detailed info
- Map API integration for area insights
- Price validation with currency support
- Trip-type aware recommendations

###  Intelligent Activity Planning
- Hobby-specific activity searches
- Duration-based scheduling rules:
  - ≤ 4 hours: Can schedule other activities
  - > 4 hours: Following activity must be ≤ 3 hours
  - ≥ 8 hours: Cancels other activities for the day
- Map API for top attractions

### Price Accuracy
## Runtime Settings

- SPEED_MODE
  - 1 (default): Minimizes Tavily usage for faster, cheaper runs. Still performs one Tavily search for activities context and basic searches for flights/stays.
  - 0: Uses enhanced Tavily flows (search+extract, optional map/crawl) and optional LLM refinements for richer results.

- AGENT_TIMEOUT_SECONDS
  - Per-agent timeout for the parallel phase. Defaults to 20 seconds when SPEED_MODE=1, and 40 seconds when SPEED_MODE=0.

- Enhanced price parsing (avoids years/discounts)
- Context-aware validation
- Multi-currency support (USD, EUR, KES, GBP)
- Reasonableness checks

## Example Usage

### Python
```python
import requests

response = requests.post("http://localhost:8000/plan-trip", json={
    "origin": "NBO",
    "destination": "Dubai",
    "start_date": "2025-11-10",
    "end_date": "2025-11-16",
    "hobbies": ["night life", "fine dining"],
    "trip_type": "honeymoon"
})

plan = response.json()["plan"]
print(f"Found {len(plan['flights'])} flights and {len(plan['stays'])} hotels")
```

### JavaScript
```javascript
const response = await fetch('http://localhost:8000/plan-trip', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    origin: 'NBO',
    destination: 'Dubai',
    start_date: '2025-11-10',
    end_date: '2025-11-16',
    hobbies: ['night life', 'fine dining'],
    trip_type: 'honeymoon'
  })
});

const data = await response.json();
console.log('Trip plan:', data.plan);
```

## Interactive Documentation

Visit http://localhost:8000/docs for Swagger UI with:
- Interactive API testing
- Request/response schemas
- Example requests
- Try-it-out functionality

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid dates, missing fields)
- `500`: Internal server error

Error responses include detailed messages:
```json
{
  "detail": "End date must be after start date"
}
```

## Development

### Running in Development Mode
```bash
python run_server.py
```
The server runs with auto-reload enabled.

### Testing
```bash
python test_api.py
```

### API Documentation
The API automatically generates OpenAPI/Swagger documentation available at `/docs`.
