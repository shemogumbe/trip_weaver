"""
Google Places API Integration for TripWeaver

This module provides Google Places API integration for finding real venues
and locations for activity generation.

Free tier provides good coverage for most destinations.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import googlemaps
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Google Maps client
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
if GOOGLE_PLACES_API_KEY:
    gmaps = googlemaps.Client(key=GOOGLE_PLACES_API_KEY)
    logger.info("Google Places API initialized")
else:
    gmaps = None
    logger.warning("GOOGLE_PLACES_API_KEY not found in environment variables")


class GooglePlacesClient:
    """Google Places API client for finding venues by hobby/activity type"""
    
    def __init__(self):
        self.client = gmaps
        
        # Hobby to Google Places type mapping
        self.hobby_place_types = {
            'dining': ['restaurant'],
            'fine dining': ['restaurant'], 
            'restaurants': ['restaurant'],
            'nightlife': ['night_club', 'bar'],
            'bars': ['bar'],
            'shopping': ['shopping_mall', 'store'],
            'golf': ['golf_course'],
            'beach': ['natural_feature'],  # Will use keyword search
            'culture': ['museum', 'art_gallery', 'tourist_attraction'],
            'wellness': ['spa', 'gym'],
            'outdoor': ['park'],
            'adventure': ['tourist_attraction'],
            'entertainment': ['amusement_park', 'movie_theater']
        }
        
        # Keywords for more specific searches
        self.hobby_keywords = {
            'fine dining': ['fine dining', 'upscale', 'michelin', 'gourmet'],
            'nightlife': ['nightclub', 'rooftop bar', 'cocktail'],
            'beach': ['beach', 'waterfront', 'coastal'],
            'adventure': ['adventure', 'tours', 'experience'],
            'wellness': ['spa', 'massage', 'wellness center'],
            'culture': ['museum', 'art', 'cultural center', 'heritage']
        }
    
    def get_location_coordinates(self, location: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a location name"""
        if not self.client:
            return None
            
        try:
            geocode_result = self.client.geocode(location)
            if geocode_result:
                coords = geocode_result[0]['geometry']['location']
                return (coords['lat'], coords['lng'])
        except Exception as e:
            logger.warning(f"Geocoding failed for {location}: {e}")
        
        return None
    
    def search_places_by_hobby(self, hobby: str, location: str, radius: int = 25000) -> List[Dict[str, Any]]:
        """
        Search for places related to a specific hobby
        
        Args:
            hobby: The hobby/activity type (e.g., 'fine dining', 'golf')
            location: Location name (e.g., 'Dubai', 'Nairobi')
            radius: Search radius in meters (default 25km)
            
        Returns:
            List of place dictionaries with name, address, rating, etc.
        """
        if not self.client:
            logger.warning("Google Places API not available")
            return []
        
        # Get coordinates for the location
        coordinates = self.get_location_coordinates(location)
        if not coordinates:
            logger.warning(f"Could not get coordinates for {location}")
            return []
        
        lat, lng = coordinates
        logger.info(f"Searching for {hobby} places near {location} ({lat}, {lng})")
        
        all_places = []
        
        # Get place types for this hobby
        hobby_lower = hobby.lower().replace(' ', '').replace('_', '')
        place_types = []
        
        # Find matching place types
        for key, types in self.hobby_place_types.items():
            if key.replace(' ', '').replace('_', '') in hobby_lower or hobby_lower in key.replace(' ', '').replace('_', ''):
                place_types.extend(types)
        
        if not place_types:
            place_types = ['establishment']  # Fallback
        
        # Search by place types
        for place_type in place_types[:2]:  # Limit to prevent too many API calls
            try:
                places_result = self.client.places_nearby(
                    location=(lat, lng),
                    radius=radius,
                    type=place_type,
                    open_now=False  # Include places that might be closed now
                )
                
                if places_result.get('results'):
                    all_places.extend(places_result['results'][:10])  # Top 10 per type
                    logger.info(f"Found {len(places_result['results'])} places for type {place_type}")
                
            except Exception as e:
                logger.warning(f"Places search failed for type {place_type}: {e}")
                continue
        
        # Also try keyword-based search for better results
        keywords = self.hobby_keywords.get(hobby.lower(), [hobby])
        for keyword in keywords[:2]:  # Limit keywords
            try:
                keyword_result = self.client.places_nearby(
                    location=(lat, lng),
                    radius=radius,
                    keyword=keyword,
                    open_now=False
                )
                
                if keyword_result.get('results'):
                    all_places.extend(keyword_result['results'][:8])  # Top 8 per keyword
                    logger.info(f"Found {len(keyword_result['results'])} places for keyword {keyword}")
                    
            except Exception as e:
                logger.warning(f"Keyword search failed for {keyword}: {e}")
                continue
        
        # Remove duplicates based on place_id
        unique_places = []
        seen_ids = set()
        
        for place in all_places:
            place_id = place.get('place_id')
            if place_id and place_id not in seen_ids:
                seen_ids.add(place_id)
                unique_places.append(place)
        
        logger.info(f"Found {len(unique_places)} unique places for {hobby} in {location}")
        return unique_places[:20]  # Return top 20
    
    def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific place"""
        if not self.client:
            return None
            
        try:
            details_result = self.client.place(
                place_id=place_id,
                fields=['name', 'formatted_address', 'rating', 'price_level', 
                       'opening_hours', 'website', 'formatted_phone_number', 'reviews']
            )
            return details_result.get('result')
        except Exception as e:
            logger.warning(f"Failed to get details for place {place_id}: {e}")
            return None
    
    def format_places_for_llm(self, places: List[Dict[str, Any]], hobby: str) -> str:
        """Format places data for LLM consumption"""
        if not places:
            return f"No places found for {hobby}."
        
        formatted_places = []
        
        for i, place in enumerate(places[:15], 1):  # Limit to top 15
            name = place.get('name', 'Unknown')
            address = place.get('vicinity', place.get('formatted_address', 'Address not available'))
            rating = place.get('rating', 0)
            price_level = place.get('price_level', 0)
            
            # Format price level
            price_symbols = {0: '$', 1: '$', 2: '$$', 3: '$$$', 4: '$$$$'}
            price_str = price_symbols.get(price_level, '$')
            
            place_str = f"{i}. {name}\n   Location: {address}\n   Rating: {rating}/5 ({price_str})"
            formatted_places.append(place_str)
        
        return "\n\n".join(formatted_places)


# Global instance
google_places_client = GooglePlacesClient()