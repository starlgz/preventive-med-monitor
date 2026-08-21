from pydantic import BaseModel
from typing import Optional, Dict, Any

class PipelineRunRequest(BaseModel):
    source_key: Optional[str] = None
    auto_push_notifications: Optional[bool] = True

class PipelineRunResponse(BaseModel):
    status: str
    stats: Dict[str, Any]
