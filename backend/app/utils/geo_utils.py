import math
from typing import List, Tuple, Dict, Any

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points 
    on the Earth surface using the Haversine formula.
    
    Returns distance in kilometers.
    """
    R = 6371.0  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon / 2) ** 2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def bearing(start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> float:
    """
    Calculate the initial bearing from one point to another.
    
    Returns bearing in degrees (0-360).
    """
    start_lat_rad = math.radians(start_lat)
    start_lon_rad = math.radians(start_lon)
    end_lat_rad = math.radians(end_lat)
    end_lon_rad = math.radians(end_lon)
    
    delta_lon = end_lon_rad - start_lon_rad
    
    y = math.sin(delta_lon) * math.cos(end_lat_rad)
    x = math.cos(start_lat_rad) * math.sin(end_lat_rad) - \
        math.sin(start_lat_rad) * math.cos(end_lat_rad) * math.cos(delta_lon)
    
    bearing_rad = math.atan2(y, x)
    bearing_deg = math.degrees(bearing_rad)
    
    return (bearing_deg + 360) % 360

def point_in_polygon(lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.
    
    Args:
        lat, lon: Point coordinates
        polygon: List of (lat, lon) tuples defining polygon vertices
    
    Returns:
        True if point is inside polygon, False otherwise
    """
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        if ((yi > lon) != (yj > lon)) and \
           (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
            inside = not inside
        
        j = i
    
    return inside

def create_circle_polygon(center_lat: float, center_lon: float, radius_km: float, segments: int = 32) -> List[List[float]]:
    """
    Create a polygon representing a circle around a center point.
    
    Used for visualizing threat zones on maps.
    """
    polygon = []
    
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        # Simplified conversion (for small radii)
        lat_offset = (radius_km / 111.0) * math.cos(angle)  # ~111km per degree latitude
        lon_offset = (radius_km / (111.0 * math.cos(math.radians(center_lat)))) * math.sin(angle)
        
        polygon.append([
            center_lat + lat_offset,
            center_lon + lon_offset
        ])
    
    return polygon

def generate_geojson_polygon(center: Dict[str, float], radius_km: float) -> Dict[str, Any]:
    """Generate GeoJSON feature for a circular zone"""
    
    polygon = create_circle_polygon(center["lat"], center["lon"], radius_km)
    
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [polygon]
        },
        "properties": {
            "center": center,
            "radius_km": radius_km
        }
    }