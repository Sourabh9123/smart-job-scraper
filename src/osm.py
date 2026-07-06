import time
import requests
from typing import List, Dict, Any, Tuple
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional

class OSMCompany(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    lat: float
    lon: float
    office_type: Optional[str] = None
    brand: Optional[str] = None
    operator: Optional[str] = None
    osm_id: int
    processed: bool = False # Flag to track if we've scraped it

class OverpassAPIError(Exception): pass
class OverpassRateLimitError(OverpassAPIError): pass
class OverpassTimeoutError(OverpassAPIError): pass
class LocationNotFoundError(Exception): pass

def build_bbox_query(south: float, west: float, north: float, east: float) -> str:
    bbox = f"{south},{west},{north},{east}"
    return f"""
[out:json][timeout:30];
(
  node["office"]({bbox});
  way["office"]({bbox});
  relation["office"]({bbox});
  node["company"]({bbox});
  way["company"]({bbox});
  relation["company"]({bbox});
  node["business"]({bbox});
  way["business"]({bbox});
  relation["business"]({bbox});
);
out center;
"""

class OSMClient:
    def __init__(self):
        self.api_url = "https://overpass-api.de/api/interpreter"
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {"User-Agent": "hiring-radar/1.0 (contact@example.com)"}
        self.timeout = 30
        self.max_retries = 3
        
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        retries = 0
        backoff = 2
        
        while retries <= self.max_retries:
            try:
                response = requests.post(self.api_url, data={"data": query}, headers=self.headers, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json().get("elements", [])
                if response.status_code == 429:
                    raise OverpassRateLimitError("Rate limit exceeded.")
                if response.status_code in [500, 502, 503]:
                    raise OverpassAPIError(f"Server error: {response.status_code}")
                response.raise_for_status()
            except (requests.exceptions.Timeout, OverpassTimeoutError) as e:
                if retries == self.max_retries: raise OverpassTimeoutError("Timeout") from e
            except Exception as e:
                if retries == self.max_retries: raise OverpassAPIError(f"Failed: {e}") from e
                
            retries += 1
            time.sleep(backoff ** retries)
        return []

    def _parse_elements(self, elements: List[Dict[str, Any]]) -> List[OSMCompany]:
        companies = []
        for el in elements:
            tags = el.get("tags", {})
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if not lat or not lon: continue
            
            name = tags.get("name") or tags.get("brand") or tags.get("operator")
            if not name: continue # We need a name to search on Serper
            
            address = " ".join([p for p in [tags.get("addr:housenumber", ""), tags.get("addr:street", "")] if p]).strip() or None
            
            company = OSMCompany(
                name=name,
                website=tags.get("website") or tags.get("contact:website"),
                phone=tags.get("phone") or tags.get("contact:phone"),
                email=tags.get("email") or tags.get("contact:email"),
                address=address,
                city=tags.get("addr:city"),
                lat=lat,
                lon=lon,
                office_type=tags.get("office"),
                brand=tags.get("brand"),
                operator=tags.get("operator"),
                osm_id=el["id"]
            )
            companies.append(company)
        return companies

    def search_location(self, location_name: str) -> List[OSMCompany]:
        params = {"q": location_name, "format": "json", "limit": 1}
        response = requests.get(self.nominatim_url, params=params, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data: raise LocationNotFoundError(f"Could not find location: {location_name}")
            
        boundingbox = data[0]["boundingbox"]
        south, north, west, east = map(float, boundingbox)
        query = build_bbox_query(south, west, north, east)
        elements = self.execute_query(query)
        return self._parse_elements(elements)
