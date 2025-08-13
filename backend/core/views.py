"""
API views for the Elevate Charter system.
"""

import json
import re
from datetime import date, timedelta
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import TripRequest
from .services import TripService, ChatService
from .repository import airport_repo, aircraft_repo
from typing import Optional


class QuoteViewHandler:
    """Handler for quote-related API endpoints."""
    
    def __init__(self):
        self.trip_service = TripService()
    
    def handle_quote_request(self, request_data: dict) -> dict:
        """Handle a quote request and return pricing options."""
        try:
            # Create trip request object
            trip_request = TripRequest(
                origin=request_data['origin'],
                destination=request_data['destination'],
                departure_date=date.fromisoformat(request_data['departure_date']),
                return_date=date.fromisoformat(request_data['return_date']) if request_data.get('return_date') else None,
                passengers=int(request_data['passengers'])
            )
            
            # Process the trip request
            quote_response = self.trip_service.process_trip_request(trip_request)
            
            # Return the response
            return quote_response.to_dict()
            
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data: {e}")
        except Exception as e:
            raise ValueError(f"Processing error: {e}")


class ChatViewHandler:
    """Handler for chat-based API endpoints."""
    
    def __init__(self):
        # Initialize OpenAI client if available
        openai_client = None
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            try:
                import openai
                openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
        
        self.chat_service = ChatService(openai_client)
        self.trip_service = TripService()
    
    def handle_chat_message(self, message: str, conversation_history: list = None) -> dict:
        """Handle a chat message and return appropriate response."""
        # Try OpenAI processing first
        try:
            response = self.chat_service.process_chat_message(message, conversation_history)
            if response and 'error' not in response:
                return response
        except Exception as e:
            print(f"OpenAI processing failed: {e}")
        
        # Fallback to regex parsing
        print("Falling back to regex parsing")
        return self._parse_with_regex(message)
    
    def _parse_with_regex(self, message: str) -> dict:
        """Parse travel request using regex patterns."""
        # Extract origin and destination
        origin, destination = self._extract_route(message)
        if not origin or not destination:
            return {
                'reply': "Missing: origin, destination.",
                'need': ['origin', 'destination'],
                'parsed': {'origin': None, 'destination': None, 'passengers': 1, 'departure_date': None, 'return_date': None}
            }
        
        # Extract departure date
        departure_date = self._extract_departure_date(message)
        if not departure_date:
            return {
                'reply': "Missing: departure date.",
                'need': ['departure date'],
                'parsed': {'origin': origin, 'destination': destination, 'passengers': 1, 'departure_date': None, 'return_date': None}
            }
        
        # Extract passengers
        passengers = self._extract_passengers(message)
        
        # Extract return date
        return_date = self._extract_return_date(message, departure_date)
        
        # Generate quote
        try:
            trip_request = TripRequest(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                passengers=passengers
            )
            
            quote_response = self.trip_service.process_trip_request(trip_request)
            
            # Generate response message
            if return_date:
                reply = f"Charter: {passengers} pax on {quote_response.recommended_aircraft.aircraft.type} from {origin} to {destination} with return. Total: ${quote_response.recommended_aircraft.total_price_usd:,.0f} USD."
            else:
                reply = f"Charter: {passengers} pax on {quote_response.recommended_aircraft.aircraft.type} from {origin} to {destination}. Total: ${quote_response.recommended_aircraft.total_price_usd:,.0f} USD."
            
            return {
                'reply': reply,
                'itinerary': quote_response.to_dict()['itinerary'],
                'legs': [quote_response.recommended_aircraft.outbound_leg.to_dict()],
                'currency': 'USD',
                'total_price_usd': float(quote_response.recommended_aircraft.total_price_usd),
                'aircraft_options': quote_response.to_dict()['aircraft_options'],
                'recommended_aircraft': quote_response.to_dict()['recommended_aircraft'],
            }
            
        except Exception as e:
            return {
                'reply': f"Error calculating quote: {str(e)}. Please try again.",
                'error': str(e)
            }
    
    def _extract_route(self, message: str) -> tuple:
        """Extract origin and destination from message."""
        # Multiple patterns for route extraction
        patterns = [
            r"from\s+([A-Za-z\s]+?)\s+to\s+([A-Za-z\s]+)",  # "from X to Y"
            r"([A-Za-z\s]+?)\s+to\s+([A-Za-z\s]+)",         # "X to Y"
            r"([A-Za-z\s]+?)\s+→\s+([A-Za-z\s]+)",          # "X → Y"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.I)
            if match:
                origin = airport_repo.find_airport(match.group(1).strip())
                destination = airport_repo.find_airport(match.group(2).strip())
                if origin and destination:
                    return origin.iata_code, destination.iata_code
        
        # Fallback: look for city names in the message
        cities_found = []
        for airport in airport_repo.get_all_airports():
            if airport.iata_code.lower() in message.lower() or airport.city.lower() in message.lower():
                cities_found.append(airport.iata_code)
        
        if len(cities_found) >= 2:
            return cities_found[0], cities_found[1]
        
        return None, None
    
    def _extract_departure_date(self, message: str) -> Optional[date]:
        """Extract departure date from message."""
        # Multiple patterns for date extraction
        date_patterns = [
            r"\b(next\s+weekend)",                           # "next weekend" - must come first
            r"\b(this\s+weekend)",                           # "this weekend" - must come first
            r"\b(on|depart|leav\w*)\s+([^,.]+)",           # "on Friday", "depart Monday"
            r"\b([A-Za-z]+\s+\d{1,2})",                     # "Friday 15", "Dec 20"
            r"\b(next\s+[A-Za-z]+)",                        # "next Friday", "next Monday"
            r"\b(this\s+[A-Za-z]+)",                        # "this Friday", "this Monday"
            r"\b(tomorrow|today)",                           # "tomorrow", "today"
            r"\b(weekend)",                                  # "weekend"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, message, re.I)
            if match:
                date_text = match.group(1) if "on|depart|leav" in pattern else match.group(0)
                return self._parse_date_text(date_text)
        
        return None
    
    def _extract_return_date(self, message: str, departure_date: date) -> Optional[date]:
        """Extract return date from message."""
        return_patterns = [
            r"\breturn\s+(?:on\s+)?([^,.]+)",               # "return Monday"
            r"\b(round\s+trip)",                             # "round trip"
            r"\b(back\s+on\s+[^,.]+)",                      # "back on Monday"
        ]
        
        for pattern in return_patterns:
            match = re.search(pattern, message, re.I)
            if match:
                if "round trip" in match.group(0).lower():
                    return departure_date  # For round trip, return same as departure
                else:
                    return self._parse_date_text(match.group(1))
        
        return None
    
    def _extract_passengers(self, message: str) -> int:
        """Extract passenger count from message."""
        pax_patterns = [
            r"\bfor\s+(\d+)\s*(pax|people|passengers)?\b",  # "for 4 people"
            r"\b(\d+)\s*(pax|people|passengers)\b",          # "4 passengers"
            r"\b(\d+)\s+people",                             # "4 people"
            r"\b(\d+)\s+pax",                                # "4 pax"
        ]
        
        for pattern in pax_patterns:
            match = re.search(pattern, message, re.I)
            if match:
                return int(match.group(1))
        
        return 1  # Default to 1 passenger
    
    def _parse_date_text(self, date_text: str) -> Optional[date]:
        """Parse date from various text formats."""
        date_text = date_text.strip().lower()
        
        # Handle special cases
        if "next weekend" in date_text:
            today = date.today()
            days_until_weekend = (5 - today.weekday()) % 7
            if days_until_weekend == 0:  # Today is Saturday
                days_until_weekend = 7
            return today + timedelta(days=days_until_weekend)
        
        elif "this weekend" in date_text:
            today = date.today()
            days_until_weekend = (5 - today.weekday()) % 7
            if days_until_weekend == 0:  # Today is Saturday
                return today
            else:
                return today + timedelta(days=days_until_weekend)
        
        elif date_text in ["tomorrow", "today"]:
            return date.today() if date_text == "today" else date.today() + timedelta(days=1)
        
        # For other cases, try to parse with dateutil or return None
        # In a production system, you'd use a proper date parsing library
        return None


# Global handlers
quote_handler = QuoteViewHandler()
chat_handler = ChatViewHandler()


@csrf_exempt
def quote_view(request):
    """Handle manual quote requests."""
    if request.method != 'POST':
        return HttpResponseBadRequest('POST only')
    
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')
    
    try:
        result = quote_handler.handle_quote_request(payload)
        return JsonResponse(result)
    except ValueError as e:
        return HttpResponseBadRequest(str(e))


@csrf_exempt
def chat_view(request):
    """Handle chat-based quote requests."""
    if request.method != 'POST':
        return HttpResponseBadRequest('POST only')
    
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')
    
    message = payload.get('message', '').strip()
    conversation_history = payload.get('conversation_history', [])
    
    if not message:
        return HttpResponseBadRequest('message required')
    
    result = chat_handler.handle_chat_message(message, conversation_history)
    return JsonResponse(result)


@csrf_exempt
def status_view(request):
    """Check system status and OpenAI availability."""
    if request.method != 'GET':
        return HttpResponseBadRequest('GET only')
    
    status = {
        'status': 'ok',
        'openai_available': bool(getattr(settings, 'OPENAI_API_KEY', '')),
        'openai_model': getattr(settings, 'OPENAI_MODEL', 'Not configured'),
        'airports_count': len(airport_repo.get_all_airports()),
        'aircraft_types': len(aircraft_repo.get_all_aircraft()),
    }
    
    return JsonResponse(status)
