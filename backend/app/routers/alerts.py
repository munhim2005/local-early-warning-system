from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import math
from typing import List

from ..models import AlertEvent, AlertNode, AlertNodeTrigger, Bunker, Base
from ..schemas import AlertEventCreate, AlertEventResponse, AlertNodeStatus
from ..database import get_db
from ..services.routing_engine import calculate_routes_to_bunkers
from ..services.mqtt_client import get_mqtt_publisher
from ..utils.geo_utils import haversine_distance, point_in_polygon
from ..config import settings

router = APIRouter()

def get_radar_distance(lat1, lon1, lat2, lon2):
    """Calculate distance using Haversine formula"""
    return haversine_distance(lat1, lon1, lat2, lon2)

@router.post("/", response_model=AlertEventResponse)
async def create_alert(event_data: AlertEventCreate, db: Session = Depends(get_db)):
    """Create a new alert event (internal use by threat analyzer)"""
    
    # Validate coordinates are within reasonable bounds
    if not (-90 <= event_data.source_latitude <= 90):
        raise HTTPException(status_code=400, detail="Invalid latitude")
    if not (-180 <= event_data.source_longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid longitude")
    
    db_event = AlertEvent(**event_data.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # If not simulation and severity is high/critical, trigger MQTT broadcast
    if not event_data.is_simulation and event_data.severity_level in ["high", "critical"]:
        # Find affected nodes within the radius
        all_nodes = db.query(AlertNode).all()
        target_node_ids = []
        for node in all_nodes:
            dist = haversine_distance(node.latitude, node.longitude, event_data.source_latitude, event_data.source_longitude)
            if dist <= event_data.affected_radius_km:
                target_node_ids.append(node.node_id)
                # Record the trigger event for the node
                trigger = AlertNodeTrigger(event_id=db_event.id, node_id=node.id)
                db.add(trigger)
        
        db.commit()

        # Only broadcast if there are nodes within the affected radius
        if target_node_ids:
            mqtt = await get_mqtt_publisher()
            await mqtt.publish(
                topic=settings.MQTT_TOPICS["ALERT"],
                payload={
                    "event_id": db_event.id,
                    "type": event_data.event_type,
                    "severity": event_data.severity_level,
                    "lat": event_data.source_latitude,
                    "lon": event_data.source_longitude,
                    "radius_km": event_data.affected_radius_km,
                    "magnitude": event_data.magnitude_or_intensity,
                    "target_nodes": target_node_ids
                }
            )
    
    return db_event

@router.get("/routing")
async def get_evacuation_routing(
    user_lat: float = Query(..., description="User's current latitude"),
    user_lon: float = Query(..., description="User's current longitude"),
    include_all_bunkers: bool = False,
    db: Session = Depends(get_db)
):
    """Calculate evacuation routes to safety bunkers"""
    
    bunkers_query = db.query(Bunker).filter(Bunker.status == "operational")
    
    if not include_all_bunkers:
        bunkers_list = bunkers_query.limit(5).all()
    else:
        bunkers_list = bunkers_query.all()
    
    if not bunkers_list:
        raise HTTPException(status_code=404, detail="No available bunkers found")
    
    bunkers_data = [
        {
            "id": b.id,
            "bunker_id": b.bunker_id,
            "name": b.name,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "capacity": b.capacity,
            "current_occupants": b.current_occupants,
            "status": b.status
        } 
        for b in bunkers_list
    ]
    
    routes = await calculate_routes_to_bunkers(user_lat, user_lon, bunkers_data)
    
    return {
        "user_location": {"lat": user_lat, "lon": user_lon},
        "recommended_route": routes[0] if routes else None,
        "all_routes": routes
    }


@router.get("/", response_model=List[AlertEventResponse])
async def get_alerts(
    limit: int = 100,
    offset: int = 0,
    event_type: str = None,
    severity_level: str = None,
    is_simulation: bool = None,
    include_resolved: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(AlertEvent)
    
    if event_type:
        query = query.filter(AlertEvent.event_type == event_type)
    if severity_level:
        query = query.filter(AlertEvent.severity_level == severity_level)
    if is_simulation is not None:
        query = query.filter(AlertEvent.is_simulation == is_simulation)
    if not include_resolved:
        query = query.filter(AlertEvent.resolved_at == None)
    
    alerts = query.order_by(AlertEvent.created_at.desc()).limit(limit).offset(offset).all()
    return alerts

@router.get("/{alert_id}", response_model=AlertEventResponse)
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.acknowledged = True
    db.commit()
    return {"status": "acknowledged"}

@router.get("/nodes/status")
async def get_node_statuses(user_lat: float = None, user_lon: float = None, db: Session = Depends(get_db)):
    """Get all alert nodes with optional distance calculation"""
    nodes = db.query(AlertNode).all()
    
    result = []
    for node in nodes:
        node_data = AlertNodeStatus.model_validate(node)
        if user_lat and user_lon:
            node_data.distance_km = round(get_radar_distance(user_lat, user_lon, node.latitude, node.longitude), 2)
        result.append(node_data)
    
    return sorted(result, key=lambda x: x.distance_km or float('inf'))


@router.get("/threat-zones")
async def get_current_threat_zones(db: Session = Depends(get_db)):
    """Get all current active threat zones as polygons"""
    active_alerts = db.query(AlertEvent).filter(
        AlertEvent.resolved_at == None,
        AlertEvent.is_simulation == False
    ).all()
    
    zones = []
    for alert in active_alerts:
        zones.append({
            "id": alert.id,
            "type": alert.event_type,
            "severity": alert.severity_level,
            "center": {
                "lat": alert.source_latitude,
                "lon": alert.source_longitude
            },
            "radius_km": alert.affected_radius_km,
            "description": alert.description
        })
    
    return zones