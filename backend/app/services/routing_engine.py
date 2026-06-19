# backend/app/services/routing_engine.py
import httpx
from typing import List, Dict, Any
from ..utils.geo_utils import haversine_distance

class RoutingEngine:
    async def get_osrm_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float):
        """Get real walking route from OSRM"""
        url = f"http://router.project-osrm.org/route/v1/foot/{start_lon},{start_lat};{end_lon},{end_lat}?geometries=geojson&overview=full"
        
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "Ok" and data.get("routes"):
                        route = data["routes"][0]
                        return {
                            "distance_km": round(route["distance"] / 1000, 2),
                            "duration_minutes": round(route["duration"] / 60, 1),
                            "geometry": route["geometry"]   # GeoJSON LineString
                        }
        except Exception as e:
            print(f"OSRM API error: {e}")
        
        # Fallback to straight line
        distance = haversine_distance(start_lat, start_lon, end_lat, end_lon)
        return {
            "distance_km": round(distance, 2),
            "duration_minutes": max(1, int((distance / 5) * 60)),
            "geometry": {
                "type": "LineString",
                "coordinates": [[start_lon, start_lat], [end_lon, end_lat]]
            }
        }

async def calculate_routes_to_bunkers(user_lat: float, user_lon: float, bunkers: List[Dict], threat_zones=None):
    engine = RoutingEngine()
    routes = []
    
    for bunker in bunkers[:5]:  # Limit to 5 closest
        route_data = await engine.get_osrm_route(
            user_lat, user_lon,
            bunker["latitude"], bunker["longitude"]
        )
        
        routes.append({
            "bunker": {
                "id": bunker.get("id"),
                "bunker_id": bunker.get("bunker_id"),
                "name": bunker.get("name"),
                "latitude": bunker["latitude"],
                "longitude": bunker["longitude"],
                "capacity": bunker.get("capacity", 0),
                "current_occupants": bunker.get("current_occupants", 0),
                "status": bunker.get("status", "operational")
            },
            "distance_km": route_data["distance_km"],
            "estimated_time_minutes": route_data["duration_minutes"],
            "path_geometry": route_data["geometry"]
        })
    
    routes.sort(key=lambda x: x["distance_km"])
    return routes