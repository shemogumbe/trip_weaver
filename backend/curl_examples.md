# TripWeaver API - cURL Examples

## Start the Server
```bash
cd backend
python run_server.py
```

## Test Health Endpoint
```bash
curl -X GET "http://localhost:8000/health"
```

## Test Root Endpoint
```bash
curl -X GET "http://localhost:8000/"
```

## Plan a Trip (Main Endpoint)
```bash
curl -X POST "http://localhost:8000/plan-trip" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "NBO",
    "destination": "Dubai",
    "start_date": "2025-11-10",
    "end_date": "2025-11-16",
    "hobbies": ["night life", "fine dining", "golf"],
    "adults": 2,
    "budget_level": "mid",
    "trip_type": "honeymoon",
    "constraints": {}
  }'
```

## Plan a Trip (Different Destination)
```bash
curl -X POST "http://localhost:8000/plan-trip" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "NBO",
    "destination": "Lagos",
    "start_date": "2025-12-01",
    "end_date": "2025-12-07",
    "hobbies": ["beach", "culture", "shopping"],
    "adults": 2,
    "budget_level": "high",
    "trip_type": "vacation"
  }'
```

## Plan a Budget Trip
```bash
curl -X POST "http://localhost:8000/plan-trip" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "NBO",
    "destination": "Mombasa",
    "start_date": "2025-10-15",
    "end_date": "2025-10-18",
    "hobbies": ["beach", "wildlife"],
    "adults": 2,
    "budget_level": "low",
    "trip_type": "weekend"
  }'
```

## Legacy Endpoint (Backward Compatibility)
```bash
curl -X POST "http://localhost:8000/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "NBO",
    "destination": "Dubai",
    "start_date": "2025-11-10",
    "end_date": "2025-11-16",
    "hobbies": ["night life", "fine dining"],
    "trip_type": "honeymoon"
  }'
```

## Expected Response Format
```json
{
  "plan": {
    "flights": [
      {
        "summary": "Kenya Airways flight NBO → DXB",
        "depart_time": "08:20",
        "arrive_time": "13:00",
        "airline": "Kenya Airways",
        "stops": 0,
        "est_price": 520.0,
        "booking_links": ["https://..."]
      }
    ],
    "stays": [
      {
        "name": "Rosewood Dubai",
        "area": "Downtown Dubai",
        "est_price_per_night": 150.0,
        "score": 8.7,
        "booking_links": ["https://..."]
      }
    ],
    "activities": [
      {
        "date": "2025-11-10",
        "morning": {
          "title": "Dubai Desert Safari",
          "location": "Dubai Desert",
          "duration_hours": 4.0,
          "est_price": 60.0,
          "tags": ["adventure"]
        },
        "afternoon": null,
        "evening": null
      }
    ]
  },
  "logs": [
    {
      "stage": "Flights",
      "raw_count": 8,
      "refined_count": 3
    }
  ],
  "success": true,
  "message": "Trip plan generated for NBO to Dubai"
}
```

## Interactive API Documentation
Visit http://localhost:8000/docs for Swagger UI documentation where you can test the API interactively.
