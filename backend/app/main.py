from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
from pathlib import Path

from .config import settings
from .database import SessionLocal, engine, get_db
from .models import Base
from .routers import alerts, simulation, bunkers, ingestion
from .services.mqtt_client import MQTTPublisher
from .services.threat_analyzer import ThreatAnalyzer
from .schemas import AlertEventCreate
from .models import AlertEvent, AlertNode, AlertNodeTrigger
from .utils.geo_utils import haversine_distance

Base.metadata.create_all(bind=engine)

async def poll_live_data(app: FastAPI):
    while True:
        try:
            active_sources = getattr(app.state, 'active_sources', ['usgs', 'nasa_eonet', 'gdacs'])
            threat_analyzer = app.state.threat_analyzer
            
            network_data_list = []
            if "usgs" in active_sources:
                res = await threat_analyzer.fetch_live_usgs_data()
                network_data_list.extend(res)
            if "nasa_eonet" in active_sources:
                res = await threat_analyzer.fetch_live_eonet_data()
                network_data_list.extend(res)
            if "gdacs" in active_sources:
                res = await threat_analyzer.fetch_live_gdacs_data()
                network_data_list.extend(res)
                
            if network_data_list:
                db = SessionLocal()
                try:
                    for network in network_data_list:
                        for data_point in network.get("data_points", []):
                            analyzed = await threat_analyzer.analyze_threat_data(data_point)
                            if analyzed:
                                is_valid = await threat_analyzer.validate_and_normalize(analyzed)
                                if is_valid:
                                    duplicate = db.query(AlertEvent).filter(
                                        AlertEvent.event_type == analyzed["event_type"],
                                        AlertEvent.source_latitude == analyzed["source_latitude"],
                                        AlertEvent.source_longitude == analyzed["source_longitude"]
                                    ).first()
                                    
                                    if not duplicate:
                                        valid_keys = AlertEventCreate.model_fields.keys()
                                        filtered_analyzed = {k: v for k, v in analyzed.items() if k in valid_keys}
                                        
                                        event_data = AlertEventCreate(**filtered_analyzed)
                                        db_event = AlertEvent(**event_data.model_dump())
                                        db.add(db_event)
                                        db.commit()
                                        db.refresh(db_event)
                                        
                                        if event_data.severity_level in ["high", "critical"]:
                                            all_nodes = db.query(AlertNode).all()
                                            target_node_ids = []
                                            for node in all_nodes:
                                                dist = haversine_distance(node.latitude, node.longitude, event_data.source_latitude, event_data.source_longitude)
                                                if dist <= event_data.affected_radius_km:
                                                    target_node_ids.append(node.node_id)
                                                    trigger = AlertNodeTrigger(event_id=db_event.id, node_id=node.id)
                                                    db.add(trigger)
                                            db.commit()
                                            
                                            if target_node_ids:
                                                await app.state.mqtt.publish(
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
                finally:
                    db.close()
        except Exception as e:
            print(f"Error in background polling: {e}")
            
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.active_sources = ["usgs", "nasa_eonet", "gdacs"]
    app.state.mqtt = MQTTPublisher(settings.MQTT_BROKER, settings.MQTT_PORT)
    await app.state.mqtt.connect()
    
    app.state.threat_analyzer = ThreatAnalyzer()
    
    # Start background polling
    polling_task = asyncio.create_task(poll_live_data(app))
    
    print(f"[SYSTEM] {settings.APP_NAME} started!")
    
    yield
    
    # Shutdown
    polling_task.cancel()
    await app.state.mqtt.disconnect()
    print("[SYSTEM] Server shutting down...")

app = FastAPI(
    title=settings.APP_NAME,
    description="Local Emergency Warning System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount recorded videos
videos_dir = Path("recordings")
videos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(videos_dir)), name="videos")

# Include Routers
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["simulation"])
app.include_router(bunkers.router, prefix="/api/bunkers", tags=["bunkers"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2026-04-18T00:00:00Z"}


