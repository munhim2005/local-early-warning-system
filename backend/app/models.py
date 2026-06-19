from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="viewer")  # viewer, admin, operator
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Bunker(Base):
    __tablename__ = "bunkers"
    
    id = Column(Integer, primary_key=True, index=True)
    bunker_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity = Column(Integer, default=500)
    current_occupants = Column(Integer, default=0)
    status = Column(String, default="operational")  # operational, full, under_maintenance
    amenities = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertEvent(Base):
    __tablename__ = "alert_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # earthquake, flood, fire, chemical, test
    severity_level = Column(String, nullable=False)  # low, medium, high, critical
    description = Column(Text)
    source_latitude = Column(Float)
    source_longitude = Column(Float)
    affected_radius_km = Column(Float)
    magnitude_or_intensity = Column(Float)
    is_simulation = Column(Boolean, default=False)
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    alert_node_triggers = relationship("AlertNodeTrigger", back_populates="event")

class AlertNode(Base):
    __tablename__ = "alert_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, unique=True, nullable=False)
    location_name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    last_status_check = Column(DateTime, default=datetime.utcnow)
    is_online = Column(Boolean, default=False)
    battery_level = Column(Float, default=100.0)
    signal_strength = Column(Integer, default=0)
    
    triggers = relationship("AlertNodeTrigger", back_populates="node")

class AlertNodeTrigger(Base):
    __tablename__ = "alert_node_triggers"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("alert_events.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("alert_nodes.id"), nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    playback_duration_seconds = Column(Integer, default=30)
    
    event = relationship("AlertEvent", back_populates="alert_node_triggers")
    node = relationship("AlertNode", back_populates="triggers")

class VideoFeedConfig(Base):
    __tablename__ = "video_feed_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, unique=True, nullable=False)
    location_name = Column(String, nullable=False)
    stream_url = Column(String, nullable=True)  # RTSP/WebSocket URL
    ai_model_enabled = Column(Boolean, default=False)
    detection_types = Column(JSON, default=["person", "smoke", "fire"])
    recording_retention_hours = Column(Integer, default=24)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RecordedFootage(Base):
    __tablename__ = "recorded_footage"
    
    id = Column(Integer, primary_key=True, index=True)
    feed_config_id = Column(Integer, ForeignKey("video_feed_configs.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer)
    event_correlation_id = Column(Integer, ForeignKey("alert_events.id"))
    detected_threats = Column(JSON, default=[])
    is_archived = Column(Boolean, default=False)

class ManualDecisionLog(Base):
    __tablename__ = "manual_decision_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    decision_type = Column(String, nullable=False)  # evacuate, shelter_in_place, clear_alarm
    reason = Column(Text)
    related_event_id = Column(Integer, ForeignKey("alert_events.id"))
    action_taken = Column(Text)