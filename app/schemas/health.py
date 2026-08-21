from pydantic import BaseModel
from typing import Dict, Any

class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    database: Dict[str, Any]
    major_catalogs_count: int

class ApiOverviewResponse(BaseModel):
    message: str
    docs_url: str
    redoc_url: str
    health_url: str
