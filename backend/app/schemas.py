from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ThreatType(str, Enum):
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    FIRE = "fire"
    CHEMICAL = "chemical"
    WEATHER = "weather"
    TEST = "test"

class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class BunkerCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    capacity: int

class BunkerResponse(BaseModel):
    id: int
    bunker_id: str
    name: str
    latitude: float
    longitude: float
    capacity: int
    current_occupants: int
    status: str
    distance_km: Optional[float] = None
    
    class Config:
        from_attributes = True

class AlertEventCreate(BaseModel):
    event_type: ThreatType
    severity_level: SeverityLevel
    description: str
    source_latitude: float
    source_longitude: float
    affected_radius_km: float
    magnitude_or_intensity: Optional[float] = None
    is_simulation: bool = False

class AlertEventResponse(AlertEventCreate):
    id: int
    created_at: datetime
    acknowledged: bool
    
    class Config:
        from_attributes = True

class AlertNodeStatus(BaseModel):
    id: int
    node_id: str
    location_name: str
    latitude: float
    longitude: float
    is_online: bool
    battery_level: float
    signal_strength: int
    
    class Config:
        from_attributes = True

class RoutingResult(BaseModel):
    user_latitude: float
    user_longitude: float
    nearest_bunker: BunkerResponse
    estimated_distance_km: float
    estimated_time_minutes: float
    route_polyline: List[List[float]]
    threat_zones_to_avoid: List[Dict[str, Any]]

class SimulationRequest(BaseModel):
    pin: str
    scenario_type: str
    parameters: Dict[str, Any]

class VideoFrameData(BaseModel):
    frame_number: int
    timestamp: datetime
    detections: List[Dict[str, Any]]
    threat_probability: float
    is_alert_triggered: bool

class RecordSegmentRequest(BaseModel):
    feed_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    reason: str