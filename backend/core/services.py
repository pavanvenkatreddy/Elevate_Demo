"""
Business logic services for pricing and trip processing.
"""

import math
from datetime import date
from decimal import Decimal
from typing import List, Optional
from .models import (
    Airport, Aircraft, TripRequest, PricingBreakdown, 
    FlightLeg, AircraftOption, QuoteResponse
)
from .repository import airport_repo, aircraft_repo


class PricingService:
    """Service for calculating charter pricing."""
    
    EARTH_RADIUS_NM = 3440.065
    TAX_RATE = Decimal("0.075")
    LANDING_FEE = Decimal("600")
    SEGMENT_FEE = Decimal("350")
    MIN_BILLABLE_NM = 250
    
    @classmethod
    def calculate_distance(cls, origin: Airport, destination: Airport) -> float:
        """Calculate distance between two airports using Haversine formula."""
        def to_radians(degrees: float) -> float:
            return degrees * math.pi / 180.0
        
        lat1, lon1 = to_radians(origin.latitude), to_radians(origin.longitude)
        lat2, lon2 = to_radians(destination.latitude), to_radians(destination.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
        c = 2 * math.asin(min(1, math.sqrt(a)))
        
        return cls.EARTH_RADIUS_NM * c
    
    @classmethod
    def calculate_lead_time_multiplier(cls, departure_date: date, base_date: Optional[date] = None) -> Decimal:
        """Calculate lead time multiplier based on departure date."""
        if base_date is None:
            base_date = date.today()
        
        days_until_departure = (departure_date - base_date).days
        
        if days_until_departure <= 3:
            return Decimal("1.30")
        elif days_until_departure <= 7:
            return Decimal("1.15")
        else:
            return Decimal("1.00")
    
    @classmethod
    def calculate_weekend_multiplier(cls, departure_date: date) -> Decimal:
        """Calculate weekend multiplier (Saturday = 5, Sunday = 6)."""
        return Decimal("1.10") if departure_date.weekday() in (5, 6) else Decimal("1.00")
    
    @classmethod
    def calculate_leg_pricing(cls, distance_nm: float, aircraft: Aircraft, departure_date: date) -> PricingBreakdown:
        """Calculate pricing for a single flight leg."""
        # Calculate billable distance (minimum 250 nm)
        billable_nm = max(distance_nm, cls.MIN_BILLABLE_NM)
        
        # Base cost calculation
        base_cost = aircraft.base_nm_rate * Decimal(str(billable_nm))
        
        # Calculate multipliers
        lead_time_mult = cls.calculate_lead_time_multiplier(departure_date)
        weekend_mult = cls.calculate_weekend_multiplier(departure_date)
        total_multiplier = lead_time_mult * weekend_mult
        
        # Calculate subtotal
        subtotal = (base_cost + cls.LANDING_FEE + cls.SEGMENT_FEE) * total_multiplier
        
        # Calculate taxes
        taxes = subtotal * cls.TAX_RATE
        
        # Calculate total
        total = subtotal + taxes
        
        return PricingBreakdown(
            billable_nm=billable_nm,
            base_nm_rate=aircraft.base_nm_rate,
            base_cost=base_cost,
            landing_fee=cls.LANDING_FEE,
            segment_fee=cls.SEGMENT_FEE,
            lead_time_multiplier=lead_time_mult,
            weekend_multiplier=weekend_mult,
            subtotal=subtotal,
            taxes=taxes,
            total_usd=total
        )


class TripService:
    """Service for processing trip requests and generating quotes."""
    
    def __init__(self):
        self.pricing_service = PricingService()
    
    def process_trip_request(self, trip_request: TripRequest) -> QuoteResponse:
        """Process a trip request and generate a complete quote response."""
        # Get origin and destination airports
        origin_airport = airport_repo.find_airport(trip_request.origin)
        destination_airport = airport_repo.find_airport(trip_request.destination)
        
        if not origin_airport or not destination_airport:
            raise ValueError("Invalid origin or destination")
        
        # Calculate distance
        distance_nm = self.pricing_service.calculate_distance(origin_airport, destination_airport)
        
        # Get suitable aircraft options
        suitable_aircraft = aircraft_repo.get_aircraft_by_capacity(trip_request.passengers)
        recommended_aircraft = aircraft_repo.get_recommended_aircraft(trip_request.passengers)
        
        # Generate aircraft options with pricing
        aircraft_options = []
        for aircraft in suitable_aircraft:
            # Calculate outbound leg pricing
            outbound_pricing = self.pricing_service.calculate_leg_pricing(
                distance_nm, aircraft, trip_request.departure_date
            )
            
            outbound_leg = FlightLeg(
                origin=origin_airport.iata_code,
                destination=destination_airport.iata_code,
                distance_nm=distance_nm,
                pricing=outbound_pricing
            )
            
            # Calculate return leg if applicable
            return_leg = None
            if trip_request.return_date:
                return_pricing = self.pricing_service.calculate_leg_pricing(
                    distance_nm, aircraft, trip_request.return_date
                )
                
                return_leg = FlightLeg(
                    origin=destination_airport.iata_code,
                    destination=origin_airport.iata_code,
                    distance_nm=distance_nm,
                    pricing=return_pricing
                )
            
            # Calculate total price
            total_price = outbound_pricing.total_usd
            if return_leg:
                total_price += return_leg.pricing.total_usd
            
            # Create aircraft option
            aircraft_option = AircraftOption(
                aircraft=aircraft,
                total_price_usd=total_price,
                outbound_leg=outbound_leg,
                return_leg=return_leg,
                is_recommended=(aircraft == recommended_aircraft)
            )
            
            aircraft_options.append(aircraft_option)
        
        # Sort by price (lowest first)
        aircraft_options.sort(key=lambda x: x.total_price_usd)
        
        # Get recommended aircraft option
        recommended_option = next(
            (opt for opt in aircraft_options if opt.is_recommended),
            aircraft_options[0] if aircraft_options else None
        )
        
        if not recommended_option:
            raise ValueError("No suitable aircraft found")
        
        return QuoteResponse(
            trip_request=trip_request,
            aircraft_options=aircraft_options,
            recommended_aircraft=recommended_option
        )


class ChatService:
    """Service for processing chat-based trip requests."""
    
    def __init__(self, openai_client=None):
        self.openai_client = openai_client
        self.trip_service = TripService()
    
    def extract_trip_info(self, message: str, conversation_history: list = None) -> Optional[TripRequest]:
        """Extract trip information from a natural language message using OpenAI."""
        if not self.openai_client:
            return None
            
        try:
            # Create a prompt for OpenAI to extract travel information
            system_prompt = """You are a travel assistant that extracts flight information from natural language requests.
            
            Extract the following information and return ONLY a JSON object:
            - origin: Airport code or city name (e.g., "BOS", "Boston")
            - destination: Airport code or city name (e.g., "LAX", "Los Angeles") 
            - departure_date: Date in YYYY-MM-DD format (e.g., "2024-08-16")
            - return_date: Date in YYYY-MM-DD format or null if one-way
            - passengers: Number of passengers (default to 1 if not specified)
            
            CRITICAL: For follow-up questions and updates, you MUST use the conversation context to fill in missing details.
            
            Follow-up question patterns:
            - "bigger aircraft" → Use previous origin/destination/dates, increase passengers to 4-6, upgrade aircraft size
            - "larger jet" → Use previous origin/destination/dates, increase passengers to 4-6, upgrade aircraft size
            - "for X people" → Use previous origin/destination/dates, update passengers
            - "return flight" → Use previous origin/destination, add return_date
            - "change to X passengers" → Use previous origin/destination/dates, update passengers
            - "is there a bigger aircraft" → Use previous origin/destination/dates, increase passengers to 4-6, upgrade aircraft size
            - "show me other options" → Use previous origin/destination/dates, keep same passengers
            - "for next friday" → Use previous origin/destination, update departure_date to next Friday
            - "i want a bigger flight" → Use previous origin/destination/dates, increase passengers to 4-6, upgrade aircraft size
            - "many guests" → Use previous origin/destination/dates, increase passengers to 8-12
            - "biggest aircraft possible" → Use previous origin/destination/dates, increase passengers to 8-12
            - "large group" → Use previous origin/destination/dates, increase passengers to 8-12
            - "change aircraft to X" → Use previous origin/destination/dates/passengers, update aircraft preference
            - "update departure to X" → Use previous origin/destination/passengers, update departure_date
            
            RULE: If the user asks a follow-up question without specifying origin/destination/dates, 
            you MUST use the values from the previous conversation context.
            
            RULE: If the user provides partial information, extract what you can and leave missing fields as null.
            
            Examples:
            "I need a jet from BOS to LAX on Friday" → {"origin": "BOS", "destination": "LAX", "departure_date": "2024-08-16", "return_date": null, "passengers": 1}
            "bigger aircraft" → {"origin": "BOS", "destination": "LAX", "departure_date": "2024-08-16", "return_date": null, "passengers": 1}
            "for 10 people" → {"origin": "BOS", "destination": "LAX", "departure_date": "2024-08-16", "return_date": null, "passengers": 10}
            "from BOS" → {"origin": "BOS", "destination": null, "departure_date": null, "return_date": null, "passengers": 1}
            
            Return ONLY the JSON object, no other text."""
            
            # Build messages with conversation history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history for context
            if conversation_history:
                print(f"Conversation history: {conversation_history}")
                for msg in conversation_history[-3:]:  # Last 3 messages for context
                    messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            print(f"Full messages sent to OpenAI: {messages}")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,
                max_tokens=200
            )
            
            # Extract the JSON response
            content = response.choices[0].message.content.strip()
            
            # Try to parse the JSON response
            import json
            import re
            from datetime import date
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # Convert date strings to date objects
                departure_date = date.fromisoformat(data['departure_date']) if data.get('departure_date') else None
                return_date = date.fromisoformat(data['return_date']) if data.get('return_date') else None
                
                return TripRequest(
                    origin=data['origin'],
                    destination=data['destination'],
                    departure_date=departure_date,
                    return_date=return_date,
                    passengers=data.get('passengers', 1)
                )
            
            return None
            
        except Exception as e:
            print(f"OpenAI extraction failed: {e}")
            return None
    
    def process_chat_message(self, message: str, conversation_history: list = None) -> dict:
        """Process a chat message and return appropriate response."""
        # Try OpenAI extraction first
        print(f"OpenAI client available: {self.openai_client is not None}")
        if self.openai_client:
            print("Attempting OpenAI extraction...")
            trip_request = self.extract_trip_info(message, conversation_history)
            print(f"OpenAI extraction result: {trip_request}")
            
            if trip_request:
                # Check if we have all required details
                missing_details = self._check_missing_details(trip_request)
                
                if missing_details:
                    # Ask for missing details
                    return self._ask_for_missing_details(missing_details, trip_request, conversation_history)
                else:
                    # Generate quote with complete information
                    try:
                        quote_response = self.trip_service.process_trip_request(trip_request)
                        return {
                            'reply': f"Charter: {trip_request.passengers} pax on {quote_response.recommended_aircraft.aircraft.type} from {trip_request.origin} to {trip_request.destination}. Total: ${quote_response.recommended_aircraft.total_price_usd:,.0f} USD.",
                            'itinerary': quote_response.to_dict()['itinerary'],
                            'legs': [quote_response.recommended_aircraft.outbound_leg.to_dict()],
                            'currency': 'USD',
                            'total_price_usd': float(quote_response.recommended_aircraft.total_price_usd),
                            'aircraft_options': quote_response.to_dict()['aircraft_options'],
                            'recommended_aircraft': quote_response.to_dict()['recommended_aircraft'],
                        }
                    except Exception as e:
                        return {'reply': f"Error processing request: {str(e)}", 'error': str(e)}
            else:
                # OpenAI couldn't extract info, ask for clarification
                return self._ask_for_clarification(message, conversation_history)
        
        # Fallback response
        return {
            'reply': "I couldn't understand your request. Please try rephrasing or use the manual quote form.",
            'error': 'OpenAI processing failed'
        }
    
    def _check_missing_details(self, trip_request: TripRequest) -> list:
        """Check what details are missing from the trip request."""
        missing = []
        
        if not trip_request.origin:
            missing.append('origin')
        if not trip_request.destination:
            missing.append('destination')
        if not trip_request.departure_date:
            missing.append('departure_date')
        if not trip_request.passengers or trip_request.passengers < 1:
            missing.append('passengers')
        
        return missing
    
    def _ask_for_missing_details(self, missing_details: list, partial_request: TripRequest, conversation_history: list = None) -> dict:
        """Generate a response asking for missing details."""
        # Build context from partial request
        context = []
        if partial_request.origin:
            context.append(f"origin: {partial_request.origin}")
        if partial_request.destination:
            context.append(f"destination: {partial_request.destination}")
        if partial_request.departure_date:
            context.append(f"date: {partial_request.departure_date}")
        if partial_request.passengers and partial_request.passengers > 0:
            context.append(f"passengers: {partial_request.passengers}")
        
        context_str = ", ".join(context) if context else "no details"
        
        # Generate appropriate question based on what's missing
        if len(missing_details) == 1:
            if 'origin' in missing_details:
                question = f"I see you want to go to {partial_request.destination}. Where are you departing from?"
            elif 'destination' in missing_details:
                question = f"I see you're departing from {partial_request.origin}. Where would you like to go?"
            elif 'departure_date' in missing_details:
                question = f"Great! When would you like to depart from {partial_request.origin} to {partial_request.destination}?"
            elif 'passengers' in missing_details:
                question = f"How many passengers will be traveling from {partial_request.origin} to {partial_request.destination}?"
        else:
            question = f"I have some details: {context_str}. I still need: {', '.join(missing_details)}. Can you provide these?"
        
        return {
            'reply': question,
            'missing_details': missing_details,
            'partial_request': {
                'origin': partial_request.origin,
                'destination': partial_request.destination,
                'departure_date': partial_request.departure_date.isoformat() if partial_request.departure_date else None,
                'return_date': partial_request.return_date.isoformat() if partial_request.return_date else None,
                'passengers': partial_request.passengers
            }
        }
    
    def _ask_for_clarification(self, message: str, conversation_history: list = None) -> dict:
        """Ask for clarification when the message is unclear."""
        return {
            'reply': "I'm not sure I understood your request. Could you please specify:\n• Where you're departing from\n• Where you're going\n• When you want to travel\n• How many passengers",
            'missing_details': ['origin', 'destination', 'departure_date', 'passengers'],
            'partial_request': None
        }
