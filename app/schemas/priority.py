from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class PriorityEvalRequest(BaseModel):
    match_level: int
    is_bianzhi: int
    apply_end_date: Optional[datetime] = None
    unit_type: Optional[str] = "其他事业单位"

class PriorityEvalResponse(BaseModel):
    priority_level: str
    priority_reason: str
    is_expiring_soon: bool

class DeduplicateRequest(BaseModel):
    job_a: Dict[str, Any]
    job_b: Dict[str, Any]

class DeduplicateResponse(BaseModel):
    is_duplicate: bool
    similarity_score: float
    reason: str

class BatchPriorityResponse(BaseModel):
    status: str
    total_jobs: int
    level_s: int
    level_a: int
    level_b: int
    level_c: int
    level_d: int
