import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from ..config import settings
from ..schemas import ThreatType, SeverityLevel
import httpx

class ThreatAnalyzer:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def analyze_threat_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse data from all available sources"""
        
        try:
            # Extract earthquake data if present
            if "earthquake" in raw_data.get("source", "").lower():
                return await self._parse_earthquake(raw_data)
            elif raw_data.get("source") == "nasa_eonet":
                return await self._parse_eonet(raw_data)
            elif raw_data.get("source") == "gdacs":
                return await self._parse_gdacs(raw_data)
        except Exception as e:
            print(f"Error analyzing threat data: {e}")
        
        return None
    
    async def _parse_earthquake(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse earthquake-specific data"""
        
        # Try multiple field names
        magnitude = data.get("magnitude") or data.get("mag") or data.get("mb")
        if magnitude:
            magnitude = float(magnitude)
        else:
            return None
        
        # Determine severity based on magnitude
        if magnitude < settings.EARTHQUAKE_MAG_THRESHOLD:
            severity = SeverityLevel.LOW
        elif magnitude < 6.0:
            severity = SeverityLevel.MEDIUM
        elif magnitude < 7.0:
            severity = SeverityLevel.HIGH
        else:
            severity = SeverityLevel.CRITICAL
        
        # Estimate affected radius
        radius_km = magnitude * 15
        
        return {
            "event_type": ThreatType.EARTHQUAKE.value,
            "severity_level": severity.value,
            "description": f"Earthquake detected with Magnitude {magnitude:.1f}",
            "source_latitude": data.get("latitude") or data.get("lat"),
            "source_longitude": data.get("longitude") or data.get("lon"),
            "affected_radius_km": radius_km,
            "magnitude_or_intensity": magnitude,
            "raw_source": "PMD Seismic Network"
        }
    
    
    
    async def _parse_eonet(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        category = data.get("category", "")
        cat_lower = category.lower()
        
        if "wildfire" in cat_lower or "fire" in cat_lower:
            event_type = ThreatType.FIRE
        elif "storm" in cat_lower or "weather" in cat_lower or "cyclone" in cat_lower:
            event_type = ThreatType.WEATHER
        elif "flood" in cat_lower:
            event_type = ThreatType.FLOOD
        elif "earthquake" in cat_lower:
            event_type = ThreatType.EARTHQUAKE
        else:
            return None
            
        return {
            "event_type": event_type.value,
            "severity_level": SeverityLevel.HIGH.value,
            "description": data.get("title", f"NASA EONET Event: {category}"),
            "source_latitude": data.get("latitude"),
            "source_longitude": data.get("longitude"),
            "affected_radius_km": 50.0,
            "magnitude_or_intensity": 0.0,
        }
        
    async def _parse_gdacs(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event_code = data.get("event_type", "")
        if event_code == "EQ":
            event_type = ThreatType.EARTHQUAKE
        elif event_code == "FL" or event_code == "TS":
            event_type = ThreatType.FLOOD
        elif event_code == "TC" or event_code == "WF": # TC=Cyclone, WF=Wildfire? Wait, let's just do TC=Weather
            event_type = ThreatType.WEATHER
            if event_code == "WF":
                event_type = ThreatType.FIRE
        else:
            # Let's map any unknown GDACS to a generic or ignore. 
            return None
            
        severity_val = data.get("magnitude")
        severity = SeverityLevel.MEDIUM
        if severity_val:
            try:
                val = float(severity_val)
                if val >= 2:
                    severity = SeverityLevel.CRITICAL
                elif val >= 1.5:
                    severity = SeverityLevel.HIGH
            except:
                pass
                
        return {
            "event_type": event_type.value,
            "severity_level": severity.value,
            "description": f"GDACS Alert [{event_code}]",
            "source_latitude": data.get("latitude"),
            "source_longitude": data.get("longitude"),
            "affected_radius_km": 100.0,
            "magnitude_or_intensity": float(severity_val) if severity_val else 0.0,
        }
    
    async def validate_and_normalize(self, analyzed_data: Dict[str, Any]) -> bool:
        """Validate that analyzed data meets system requirements"""
        
        required_fields = ["event_type", "severity_level", "description", 
                          "source_latitude", "source_longitude"]
        
        for field in required_fields:
            if field not in analyzed_data or analyzed_data[field] is None:
                return False
        
        # Validate coordinates
        lat = analyzed_data["source_latitude"]
        lon = analyzed_data["source_longitude"]
        
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
        
        return True
    
    async def fetch_live_usgs_data(self) -> List[Dict[str, Any]]:
        """Fetch real earthquake data from USGS"""
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
        try:
            response = await self.http_client.get(url)
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                
                mapped_data = []
                for feature in features:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry", {})
                    coords = geom.get("coordinates", [])
                    if not coords or len(coords) < 2:
                        continue
                        
                    mapped_data.append({
                        "source": "usgs_earthquake",
                        "latitude": coords[1],
                        "longitude": coords[0],
                        "magnitude": props.get("mag"),
                        "time": props.get("time")
                    })
                return [{
                    "source": "usgs_earthquake_network",
                    "last_updated": datetime.utcnow().isoformat(),
                    "data_points": mapped_data
                }]
        except Exception as e:
            print(f"Error fetching USGS data: {e}")
            
        return []

    async def fetch_live_eonet_data(self) -> List[Dict[str, Any]]:
        """Fetch natural event data from NASA EONET"""
        url = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=10"
        try:
            response = await self.http_client.get(url)
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                
                mapped_data = []
                for event in events:
                    if not event.get("geometry"):
                        continue
                    # Just taking the first geometry coordinate
                    geom = event["geometry"][0]
                    coords = geom.get("coordinates", [])
                    if not coords or len(coords) < 2:
                        continue
                        
                    mapped_data.append({
                        "source": "nasa_eonet",
                        "latitude": coords[1],
                        "longitude": coords[0],
                        "title": event.get("title"),
                        "category": event.get("categories", [{}])[0].get("title"),
                        "time": geom.get("date")
                    })
                return [{
                    "source": "nasa_eonet_network",
                    "last_updated": datetime.utcnow().isoformat(),
                    "data_points": mapped_data
                }]
        except Exception as e:
            print(f"Error fetching EONET data: {e}")
            
        return []

    async def fetch_live_gdacs_data(self) -> List[Dict[str, Any]]:
        """Fetch disaster alerts from GDACS (Global Disaster Alert and Coordination System)"""
        url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
        try:
            response = await self.http_client.get(url)
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                
                mapped_data = []
                for feature in features:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry", {})
                    coords = geom.get("coordinates", [])
                    if not coords or len(coords) < 2:
                        continue
                        
                    mapped_data.append({
                        "source": "gdacs",
                        "latitude": coords[1],
                        "longitude": coords[0],
                        "magnitude": props.get("severity"),
                        "event_type": props.get("eventtype"),
                        "time": props.get("todate")
                    })
                return [{
                    "source": "gdacs_network",
                    "last_updated": datetime.utcnow().isoformat(),
                    "data_points": mapped_data
                }]
        except Exception as e:
            print(f"Error fetching GDACS data: {e}")
            
        return []
