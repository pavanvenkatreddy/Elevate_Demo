"""
Data repository for airports and aircraft information.
"""

from typing import Dict, List, Optional
from decimal import Decimal
from .models import Airport, Aircraft


class AirportRepository:
    """Repository for airport data management."""
    
    def __init__(self):
        self._airports: Dict[str, Airport] = {}
        self._city_to_iatas: Dict[str, List[str]] = {}
        self._city_aliases: Dict[str, str] = {}
        self._initialize_airports()
    
    def _initialize_airports(self):
        """Initialize airport data."""
        # Core airports
        airports_data = [
            ("JFK", "New York", 40.6413, -73.7781),
            ("EWR", "Newark", 40.6895, -74.1745),
            ("LGA", "New York", 40.7769, -73.8740),
            ("BOS", "Boston", 42.3656, -71.0096),
            ("MIA", "Miami", 25.7959, -80.2870),
            ("FLL", "Fort Lauderdale", 26.0726, -80.1527),
            ("LAX", "Los Angeles", 33.9416, -118.4085),
            ("SFO", "San Francisco", 37.6213, -122.3790),
            ("LAS", "Las Vegas", 36.0840, -115.1537),
            ("ORD", "Chicago", 41.9742, -87.9073),
            ("DFW", "Dallas", 32.8998, -97.0403),
            ("SEA", "Seattle", 47.4502, -122.3088),
        ]
        
        # Create airport objects
        for iata, city, lat, lon in airports_data:
            airport = Airport(iata_code=iata, city=city, latitude=lat, longitude=lon)
            self._airports[iata] = airport
            
            # Build city to IATA mapping
            city_lower = city.lower()
            if city_lower not in self._city_to_iatas:
                self._city_to_iatas[city_lower] = []
            self._city_to_iatas[city_lower].append(iata)
        
        # Add city aliases
        self._city_aliases = {
            "la": "Los Angeles",
            "nyc": "New York", 
            "ny": "New York",
            "vegas": "Las Vegas",
            "sf": "San Francisco",
            "miami": "Miami",
            "chicago": "Chicago",
            "dallas": "Dallas",
            "seattle": "Seattle",
            "boston": "Boston",
        }
        
        # Add aliases to city mapping
        for alias, city in self._city_aliases.items():
            if city.lower() in self._city_to_iatas:
                self._city_to_iatas[alias] = self._city_to_iatas[city.lower()]
    
    def get_airport(self, iata_code: str) -> Optional[Airport]:
        """Get airport by IATA code."""
        return self._airports.get(iata_code.upper())
    
    def find_airport(self, token: str) -> Optional[Airport]:
        """Find airport by IATA code, city name, or alias."""
        token = token.strip()
        
        # Direct IATA code
        if token.upper() in self._airports:
            return self._airports[token.upper()]
        
        # City name or alias
        city = token.lower()
        if city in self._city_to_iatas:
            iata = self._city_to_iatas[city][0]
            return self._airports[iata]
        
        # Partial city match (require at least 3 characters)
        for city_name, iatas in self._city_to_iatas.items():
            if city in city_name and len(city) >= 3:
                return self._airports[iatas[0]]
        
        return None
    
    def get_all_airports(self) -> List[Airport]:
        """Get all airports."""
        return list(self._airports.values())
    
    def get_airports_by_city(self, city: str) -> List[Airport]:
        """Get all airports in a city."""
        city_lower = city.lower()
        if city_lower in self._city_to_iatas:
            return [self._airports[iata] for iata in self._city_to_iatas[city_lower]]
        return []


class AircraftRepository:
    """Repository for aircraft data management."""
    
    def __init__(self):
        self._aircraft: List[Aircraft] = []
        self._initialize_aircraft()
    
    def _initialize_aircraft(self):
        """Initialize aircraft data."""
        aircraft_data = [
            ("Very Light Jet", 4, Decimal("9.0"), 1200, 400, "Basic comfort"),
            ("Light Jet", 7, Decimal("11.0"), 1500, 450, "Enhanced comfort"),
            ("Midsize Jet", 9, Decimal("13.5"), 2000, 500, "Premium comfort"),
            ("Super Midsize", 10, Decimal("15.0"), 2500, 550, "Luxury comfort"),
            ("Heavy Jet", 16, Decimal("18.0"), 3000, 600, "Ultra luxury"),
        ]
        
        for type_name, capacity, rate, range_nm, speed, amenities in aircraft_data:
            aircraft = Aircraft(
                type=type_name,
                capacity=capacity,
                base_nm_rate=rate,
                range_nm=range_nm,
                cruise_speed=speed,
                amenities=amenities
            )
            self._aircraft.append(aircraft)
    
    def get_all_aircraft(self) -> List[Aircraft]:
        """Get all aircraft types."""
        return self._aircraft.copy()
    
    def get_aircraft_by_capacity(self, passengers: int) -> List[Aircraft]:
        """Get aircraft that can accommodate the given number of passengers."""
        return [ac for ac in self._aircraft if ac.can_accommodate(passengers)]
    
    def get_recommended_aircraft(self, passengers: int) -> Aircraft:
        """Get the recommended aircraft for the given number of passengers."""
        suitable_aircraft = self.get_aircraft_by_capacity(passengers)
        if not suitable_aircraft:
            return self._aircraft[-1]  # Return largest aircraft as fallback
        return suitable_aircraft[0]  # Return smallest suitable aircraft


# Global instances
airport_repo = AirportRepository()
aircraft_repo = AircraftRepository()
