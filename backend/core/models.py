"""
Core data models for the Elevate Charter system.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal


@dataclass
class Airport:
    """Represents an airport with its location and metadata."""
    iata_code: str
    city: str
    latitude: float
    longitude: float
    
    def __str__(self) -> str:
        return f"{self.iata_code} ({self.city})"


@dataclass
class Aircraft:
    """Represents an aircraft type with its specifications."""
    type: str
    capacity: int
    base_nm_rate: Decimal
    range_nm: int
    cruise_speed: int
    amenities: str
    
    def can_accommodate(self, passengers: int) -> bool:
        """Check if aircraft can accommodate the given number of passengers."""
        return passengers <= self.capacity


@dataclass
class TripRequest:
    """Represents a charter trip request."""
    origin: str
    destination: str
    departure_date: date
    return_date: Optional[date]
    passengers: int
    
    def is_round_trip(self) -> bool:
        """Check if this is a round trip."""
        return self.return_date is not None


@dataclass
class PricingBreakdown:
    """Detailed pricing breakdown for a flight leg."""
    billable_nm: float
    base_nm_rate: Decimal
    base_cost: Decimal
    landing_fee: Decimal
    segment_fee: Decimal
    lead_time_multiplier: Decimal
    weekend_multiplier: Decimal
    subtotal: Decimal
    taxes: Decimal
    total_usd: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "billable_nm": round(self.billable_nm, 1),
            "base_nm_rate": float(self.base_nm_rate),
            "base_cost": round(float(self.base_cost), 2),
            "fees": {
                "landing_fee": float(self.landing_fee),
                "segment_fee": float(self.segment_fee)
            },
            "multipliers": {
                "lead_time": round(float(self.lead_time_multiplier), 2),
                "weekend": round(float(self.weekend_multiplier), 2)
            },
            "subtotal": round(float(self.subtotal), 2),
            "taxes": round(float(self.taxes), 2),
            "total_usd": round(float(self.total_usd), 2)
        }


@dataclass
class FlightLeg:
    """Represents a single flight leg."""
    origin: str
    destination: str
    distance_nm: float
    pricing: PricingBreakdown
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "from": self.origin,
            "to": self.destination,
            "distance_nm": round(self.distance_nm, 1),
            "pricing": self.pricing.to_dict()
        }


@dataclass
class AircraftOption:
    """Represents an aircraft option with pricing."""
    aircraft: Aircraft
    total_price_usd: Decimal
    outbound_leg: FlightLeg
    return_leg: Optional[FlightLeg]
    is_recommended: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "aircraft_type": self.aircraft.type,
            "capacity": self.aircraft.capacity,
            "base_nm_rate": float(self.aircraft.base_nm_rate),
            "range_nm": self.aircraft.range_nm,
            "cruise_speed": self.aircraft.cruise_speed,
            "amenities": self.aircraft.amenities,
            "total_price_usd": round(float(self.total_price_usd), 2),
            "outbound_leg": self.outbound_leg.to_dict(),
            "return_leg": self.return_leg.to_dict() if self.return_leg else None,
            "recommended": self.is_recommended
        }


@dataclass
class QuoteResponse:
    """Complete quote response with all options."""
    trip_request: TripRequest
    aircraft_options: List[AircraftOption]
    recommended_aircraft: AircraftOption
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "itinerary": {
                "origin": self.trip_request.origin,
                "destination": self.trip_request.destination,
                "departure_date": self.trip_request.departure_date.isoformat(),
                "return_date": self.trip_request.return_date.isoformat() if self.trip_request.return_date else None,
                "passengers": self.trip_request.passengers,
                "distance_nm": self.aircraft_options[0].outbound_leg.distance_nm if self.aircraft_options else 0
            },
            "aircraft_options": [opt.to_dict() for opt in self.aircraft_options],
            "recommended_aircraft": {
                "type": self.recommended_aircraft.aircraft.type,
                "capacity": self.recommended_aircraft.aircraft.capacity,
                "total_price_usd": float(self.recommended_aircraft.total_price_usd),
                "base_nm_rate": float(self.recommended_aircraft.aircraft.base_nm_rate),
                "range_nm": self.recommended_aircraft.aircraft.range_nm,
                "cruise_speed": self.recommended_aircraft.aircraft.cruise_speed,
                "amenities": self.recommended_aircraft.aircraft.amenities
            },
            "currency": "USD",
            "total_price_usd": float(self.recommended_aircraft.total_price_usd)
        }
