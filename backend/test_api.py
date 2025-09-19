#!/usr/bin/env python3
"""
Test script for TripWeaver API
"""

import requests
import json
from datetime import date, timedelta

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_plan_trip():
    """Test the trip planning endpoint"""
    print("Testing trip planning endpoint...")
    
    # Create a test request
    trip_request = {
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
    
    print(f"Request: {json.dumps(trip_request, indent=2)}")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/plan-trip",
            json=trip_request,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Trip plan generated successfully!")
            print(f"Message: {result.get('message')}")
            print(f"Success: {result.get('success')}")
            
            plan = result.get('plan', {})
            print(f"\n📊 Plan Summary:")
            print(f"  Flights: {len(plan.get('flights', []))}")
            print(f"  Stays: {len(plan.get('stays', []))}")
            print(f"  Activity Days: {len(plan.get('activities', []))}")
            
            # Show sample data
            if plan.get('flights'):
                print(f"\n✈️ Sample Flight:")
                flight = plan['flights'][0]
                print(f"  {flight.get('summary', 'N/A')}")
                print(f"  Price: {flight.get('est_price', 'N/A')} {flight.get('currency', 'USD')}")
            
            if plan.get('stays'):
                print(f"\n🏨 Sample Stay:")
                stay = plan['stays'][0]
                print(f"  {stay.get('name', 'N/A')} in {stay.get('area', 'N/A')}")
                print(f"  Price: {stay.get('est_price_per_night', 'N/A')} {stay.get('currency', 'USD')}/night")
            
            if plan.get('activities'):
                print(f"\n🎯 Sample Activities:")
                for i, day in enumerate(plan['activities'][:2]):  # Show first 2 days
                    print(f"  Day {i+1} ({day.get('date', 'N/A')}):")
                    for slot in ['morning', 'afternoon', 'evening']:
                        activity = day.get(slot)
                        if activity:
                            print(f"    {slot.title()}: {activity.get('title', 'N/A')}")
            
            # Show logs if available
            logs = result.get('logs', [])
            if logs:
                print(f"\n📝 Processing Logs:")
                for log in logs[-3:]:  # Show last 3 logs
                    print(f"  {log.get('stage', 'Unknown')}: {log.get('raw_count', 0)} raw → {log.get('refined_count', 0)} refined")
        else:
            print("❌ Error generating trip plan")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server")
        print("Make sure the server is running: python run_server.py")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()

def test_root():
    """Test the root endpoint"""
    print("Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

if __name__ == "__main__":
    print("🚀 TripWeaver API Test Suite")
    print("=" * 50)
    
    try:
        test_root()
        test_health()
        test_plan_trip()
        
        print("✅ All tests completed!")
        print("\n💡 Tips:")
        print("  - Visit http://localhost:8000/docs for interactive API documentation")
        print("  - Use the /plan-trip endpoint for new integrations")
        print("  - The /plan endpoint is available for backward compatibility")
        
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
