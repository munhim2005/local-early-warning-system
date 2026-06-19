from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
from datetime import datetime
from typing import Dict, Any

from ..database import get_db
from ..models import AlertEvent, AlertNode, Bunker
from ..schemas import SimulationRequest
from ..config import settings
from ..services.mqtt_client import get_mqtt_publisher


router = APIRouter()

@router.post("/trigger")
async def trigger_simulation(request: SimulationRequest, db: Session = Depends(get_db)):
    """Secure endpoint to manually trigger simulated disaster scenarios"""
    
    # Verify simulation PIN
    if request.pin != settings.SIMULATION_PIN:
        raise HTTPException(status_code=403, detail="Invalid simulation PIN")
    
    scenarios = {
        "earthquake_light": {
            "type": "earthquake",
            "severity": "medium",
            "magnitude_range": [4.0, 5.5],
            "description_template": "Moderate earthquake detected affecting {location}"
        },
        "earthquake_severe": {
            "type": "earthquake", 
            "severity": "critical",
            "magnitude_range": [6.0, 7.5],
            "description_template": "SEVERE earthquake detected! {location} area under danger"
        },
        "flood_minor": {
            "type": "flood",
            "severity": "medium",
            "intensity_range": [2.5, 4.0],
            "description_template": "Flood warning issued for Rawal River vicinity"
        },
        "flood_major": {
            "type": "flood",
            "severity": "critical",
            "intensity_range": [4.5, 6.0],
            "description_template": "CRITICAL FLOOD ALERT! Immediate evacuation required"
        },
        "multi_scenario_demo": {
            "type": "custom",
            "severity": "high",
            "description_template": "Multi-hazard simulation exercise"
        }
    }
    
    if request.scenario_type not in scenarios:
        raise HTTPException(status_code=400, detail="Unknown scenario type")
    
    scenario = scenarios[request.scenario_type]
    params = request.parameters or {}
    
    # Generate realistic coordinates around Islamabad
    center_lat = settings.ISLAMABAD_CENTER_LAT
    center_lon = settings.ISLAMABAD_CENTER_LON
    variance = params.get("variance_km", 15) / 111.0  # Convert km to degrees approx
    
    sim_lat = center_lat + (random.uniform(-0.5, 0.5) * variance)
    sim_lon = center_lon + (random.uniform(-0.5, 0.5) * variance)
    
    # Create alert event
    if scenario["type"] == "earthquake":
        magnitude = random.uniform(*scenario["magnitude_range"])
        radius = magnitude * 15  # Rough estimate of affected radius
        
        description = scenario["description_template"].format(location="Islamabad Sector")
        if magnitude > 6.0:
            description = "⚠️ " + description.upper() + " ⚠️"
            
        alert_data = {
            "event_type": "earthquake",
            "severity_level": scenario["severity"],
            "description": description,
            "source_latitude": sim_lat,
            "source_longitude": sim_lon,
            "affected_radius_km": radius,
            "magnitude_or_intensity": magnitude,
            "is_simulation": True
        }
    elif scenario["type"] == "flood":
        intensity = random.uniform(*scenario["intensity_range"])
        radius = params.get("radius_km", 10)
        
        alert_data = {
            "event_type": "flood",
            "severity_level": scenario["severity"],
            "description": scenario["description_template"],
            "source_latitude": sim_lat,
            "source_longitude": sim_lon,
            "affected_radius_km": radius,
            "magnitude_or_intensity": intensity,
            "is_simulation": True
        }
    else:
        alert_data = {
            "event_type": "test",
            "severity_level": "low",
            "description": "Simulation test",
            "source_latitude": sim_lat,
            "source_longitude": sim_lon,
            "affected_radius_km": 5.0,
            "magnitude_or_intensity": None,
            "is_simulation": True
        }
    
    valid_keys = {
        "event_type", "severity_level", "description", "source_latitude",
        "source_longitude", "affected_radius_km", "magnitude_or_intensity", 
        "is_simulation"
    }
    
    # Add custom parameters if provided (but only valid ones)
    if params:
        for k, v in params.items():
            if k in valid_keys:
                alert_data[k] = v
    
    # Save to database
    db_event = AlertEvent(**alert_data)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Publish to MQTT even though it's simulation (for demo purposes)
    # In production, this would go to a separate "test" topic
    mqtt = await get_mqtt_publisher()
    await mqtt.publish(
        topic=settings.MQTT_TOPICS["ALERT"],
        payload={
            "event_id": db_event.id,
            "type": alert_data["event_type"],
            "severity": alert_data["severity_level"],
            "lat": alert_data["source_latitude"],
            "lon": alert_data["source_longitude"],
            "radius_km": alert_data["affected_radius_km"],
            "magnitude": alert_data["magnitude_or_intensity"],
            "SIMULATION": True,
            "audio_override": "TEST_MODE_ACTIVE"  # Tells edge nodes to play test tone
        }
    )
    
    return {
        "status": "success",
        "message": f"Simulation '{request.scenario_type}' triggered successfully",
        "event_id": db_event.id,
        "generated_coordinates": {
            "latitude": round(sim_lat, 6),
            "longitude": round(sim_lon, 6)
        },
        "parameters": alert_data
    }

@router.post("/reset-all")
async def reset_simulation_state(db: Session = Depends(get_db)):
    """Reset all simulation-related data"""
    
    # Mark all simulation events as resolved
    db.query(AlertEvent).filter(
        AlertEvent.is_simulation == True,
        AlertEvent.resolved_at == None
    ).update({"resolved_at": datetime.utcnow()})
    
    db.commit()
    
    return {"status": "success", "message": "All simulation events have been reset"}

@router.get("/available-scenarios")
async def list_available_scenarios():
    """Return list of available simulation scenarios"""
    return {
        "scenarios": [
            {"id": "earthquake_light", "name": "Light Earthquake (M4-5.5)", "danger_level": "moderate"},
            {"id": "earthquake_severe", "name": "Severe Earthquake (M6-7.5)", "danger_level": "critical"},
            {"id": "flood_minor", "name": "Minor Flood Warning", "danger_level": "moderate"},
            {"id": "flood_major", "name": "Major Flood Emergency", "danger_level": "critical"},
            {"id": "multi_scenario_demo", "name": "Full System Demo", "danger_level": "high"}
        ]
    }