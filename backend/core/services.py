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
    
    def extract_trip_info(self, message: str) -> Optional[TripRequest]:
        """Extract trip information from a natural language message."""
        # This would integrate with OpenAI for natural language processing
        # For now, return None to indicate fallback to regex parsing
        return None
    
    def process_chat_message(self, message: str) -> dict:
        """Process a chat message and return appropriate response."""
        # Try OpenAI extraction first
        if self.openai_client:
            trip_request = self.extract_trip_info(message)
            if trip_request:
                try:
                    quote_response = self.trip_service.process_trip_request(trip_request)
                    return {
                        'reply': f"Charter: {trip_request.passengers} pax on {quote_response.recommended_aircraft.aircraft.type} from {trip_request.origin} to {trip_request.destination}. Total: ${quote_response.recommended_aircraft.total_price_usd:,.0f} USD.",
                        'itinerary': quote_response.to_dict()['itinerary'],
                        'legs': [quote_response.recommended_aircraft.outbound_leg.to_dict()],
                        'currency': 'USD',
                        'total_price_usd': float(quote_response.recommended_aircraft.total_price_usd),
                    }
                except Exception as e:
                    return {'reply': f"Error processing request: {str(e)}", 'error': str(e)}
        
        # Fallback response
        return {
            'reply': "I couldn't understand your request. Please try rephrasing or use the manual quote form.",
            'error': 'OpenAI processing failed'
        }
