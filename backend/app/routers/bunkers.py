from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..database import SessionLocal
from ..models import Bunker
from ..schemas import BunkerResponse, BunkerCreate
from ..utils.geo_utils import haversine_distance

router = APIRouter()

# 1. STATIC ROUTES FIRST
@router.get("/force-seed")
async def force_seed_bunkers(db: Session = Depends(get_db)):
    """Manually trigger the database seed from the browser"""
    sample_bunkers = [
        {"bunker_id": "BK-G9-01", "name": "G-9 Civil Defence Post", "lat": 33.6853, "lon": 73.0298, "cap": 300},
        {"bunker_id": "BK-F6-01", "name": "F-6 Sector Assembly Point", "lat": 33.7289, "lon": 73.0732, "cap": 400},
        {"bunker_id": "BK-F7-01", "name": "F-7 Community Shelter", "lat": 33.7169, "lon": 73.0551, "cap": 250},
        {"bunker_id": "BK-CBLOCK-01", "name": "C-Block Emergency Center", "lat": 33.6962, "lon": 73.0635, "cap": 500},
        {"bunker_id": "BK-H8-01", "name": "H-8 Safety Zone", "lat": 33.6667, "lon": 73.0444, "cap": 350},
        {"bunker_id": "BK-RawalPK-01", "name": "Rawal Lake Evacuation Hub", "lat": 33.7107, "lon": 73.1364, "cap": 600},
        {"bunker_id": "BK-BlueArea-01", "name": "Blue Area Command Post", "lat": 33.7088, "lon": 73.0645, "cap": 450},
        {"bunker_id": "BK-Markaz-01", "name": "F-8 Markaz Shelter", "lat": 33.7058, "lon": 73.0416, "cap": 300},
        {"bunker_id": "BK-I8-01", "name": "Sector I-8 Assembly Point", "lat": 33.6685, "lon": 73.0763, "cap": 400},
        {"bunker_id": "BK-E7-01", "name": "E-7 Safe House", "lat": 33.7265, "lon": 73.0456, "cap": 800},
    ]
    
    count = db.query(Bunker).count()
    if count > 0:
        return {"status": "skipped", "message": f"Database already has {count} bunkers."}
        
    for bunker_data in sample_bunkers:
        bunker = Bunker(
            bunker_id=bunker_data["bunker_id"],
            name=bunker_data["name"],
            latitude=bunker_data["lat"],
            longitude=bunker_data["lon"],
            capacity=bunker_data["cap"],
            amenities={"water": True, "food": True, "medical": True, "emergency_power": True}
        )
        db.add(bunker)
    db.commit()
    
    return {"status": "success", "message": "10 Islamabad Bunkers successfully seeded!"}

@router.get("/nearest")
async def get_nearest_bunkers(
    user_lat: float = None,
    user_lon: float = None,
    limit: int = 3,
    db: Session = Depends(get_db)
):
    """Get nearest bunkers to a given location"""
    if user_lat is None or user_lon is None:
        raise HTTPException(status_code=400, detail="User coordinates required")
    
    bunkers = db.query(Bunker).filter(Bunker.status.in_(["operational", "under_maintenance"])).all()
    
    result = []
    for bunker in bunkers:
        distance = haversine_distance(user_lat, user_lon, bunker.latitude, bunker.longitude)
        result.append({
            "bunker": BunkerResponse.model_validate(bunker),
            "distance_km": round(distance, 2)
        })
    
    result.sort(key=lambda x: x["distance_km"])
    return result[:limit]

@router.get("/", response_model=List[BunkerResponse])
async def get_bunkers(
    user_lat: float = None,
    user_lon: float = None,
    limit: int = 100,
    status_filter: str = None,
    db: Session = Depends(get_db)
):
    """Get all bunkers with optional filtering and distance calculation"""
    query = db.query(Bunker)
    if status_filter:
        query = query.filter(Bunker.status == status_filter)
    
    bunkers = query.limit(limit).all()
    
    result = []
    for bunker in bunkers:
        bunker_data = BunkerResponse.model_validate(bunker)
        if user_lat and user_lon:
            bunker_data.distance_km = round(
                haversine_distance(user_lat, user_lon, bunker.latitude, bunker.longitude), 2
            )
        result.append(bunker_data)
    
    if user_lat and user_lon:
        result = sorted([b for b in result if b.distance_km is not None], key=lambda x: x.distance_km)
    
    return result

# 2. DYNAMIC ROUTES LAST
@router.post("/", response_model=BunkerResponse)
async def create_bunker(bunker_data: BunkerCreate, db: Session = Depends(get_db)):
    """Create a new bunker"""
    import uuid
    new_bunker_id = f"BK-CUSTOM-{uuid.uuid4().hex[:6].upper()}"
    
    bunker = Bunker(
        bunker_id=new_bunker_id,
        name=bunker_data.name,
        latitude=bunker_data.latitude,
        longitude=bunker_data.longitude,
        capacity=bunker_data.capacity,
        amenities={"water": True, "food": True, "medical": True, "emergency_power": True}
    )
    db.add(bunker)
    db.commit()
    db.refresh(bunker)
    return bunker

@router.get("/{bunker_id}")
async def get_bunker(bunker_id: int, db: Session = Depends(get_db)):
    bunker = db.query(Bunker).filter(Bunker.id == bunker_id).first()
    if not bunker:
        raise HTTPException(status_code=404, detail="Bunker not found")
    return bunker

@router.post("/{bunker_id}/update-occupancy")
async def update_bunker_occupancy(
    bunker_id: int,
    occupancy_change: int,
    db: Session = Depends(get_db)
):
    """Update bunker occupancy (+add people, -remove people)"""
    bunker = db.query(Bunker).filter(Bunker.id == bunker_id).first()
    if not bunker:
        raise HTTPException(status_code=404, detail="Bunker not found")
    
    new_occupancy = bunker.current_occupants + occupancy_change
    
    if new_occupancy < 0:
        raise HTTPException(status_code=400, detail="Cannot have negative occupants")
    if new_occupancy > bunker.capacity:
        bunker.current_occupants = bunker.capacity
        bunker.status = "full"
    else:
        bunker.current_occupants = new_occupancy
        if new_occupancy >= bunker.capacity:
            bunker.status = "full"
        else:
            bunker.status = "operational"
    
    db.commit()
    
    return {
        "status": "success",
        "bunker_id": bunker.bunker_id,
        "new_occupancy": bunker.current_occupants,
        "remaining_capacity": bunker.capacity - bunker.current_occupants
    }

@router.delete("/{bunker_id}")
async def delete_bunker(bunker_id: int, db: Session = Depends(get_db)):
    """Remove a bunker"""
    bunker = db.query(Bunker).filter(Bunker.id == bunker_id).first()
    if not bunker:
        raise HTTPException(status_code=404, detail="Bunker not found")
    db.delete(bunker)
    db.commit()
    return {"status": "success"}