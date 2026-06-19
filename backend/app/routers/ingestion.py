from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List

router = APIRouter()

class IngestionConfig(BaseModel):
    sources: List[str]

@router.post("/config")
async def update_ingestion_config(config: IngestionConfig, request: Request):
    """Update active ingestion sources"""
    request.app.state.active_sources = config.sources
    return {
        "status": "success", 
        "message": f"Active sources updated to {config.sources}"
    }
