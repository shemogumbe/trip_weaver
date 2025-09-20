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
