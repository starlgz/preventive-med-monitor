from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class MajorMatchRequest(BaseModel):
    major_raw: str
    unit_type: Optional[str] = "其他事业单位"
    job_name: Optional[str] = ""

class MajorMatchResponse(BaseModel):
    match_level: int
    matched_codes: List[str]
    match_reason: str

class BatchMatchResponse(BaseModel):
    status: str
    total_jobs: int
    matched_5_star: int
    matched_4_star: int
    matched_3_star: int
    matched_2_star: int
    excluded_1_star: int
