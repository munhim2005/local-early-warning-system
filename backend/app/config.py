import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Local Emergency Warning System"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/islamabad_ews"
    
    # MQTT
    MQTT_BROKER: str = "mosquitto"
    MQTT_PORT: int = 1883
    MQTT_TOPICS: dict = {
        "ALERT": "islamabad/alert/critical",
        "STATUS": "islamabad/node/status",
        "VIDEO": "islamabad/video/stream"
    }
    
    # Authentication
    SECRET_KEY: str = "your-super-secret-key-change-in-production-xyz789"
    SIMULATION_PIN: str = "ADMIN_SIM_2026_SECURE"
    
    # Geographic Bounds (Islamabad)
    ISLAMABAD_CENTER_LAT: float = 33.6844
    ISLAMABAD_CENTER_LON: float = 73.0479
    ISLAMABAD_RADIUS_KM: float = 50.0
    
    # Threat Thresholds
    EARTHQUAKE_MAG_THRESHOLD: float = 5.0
    FLOOD_LEVEL_THRESHOLD: float = 3.0  # meters
    
    class Config:
        env_file = ".env"

settings = Settings()