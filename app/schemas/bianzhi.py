from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class BianzhiEvalRequest(BaseModel):
    job_name: Optional[str] = ""
    unit_name: Optional[str] = ""
    unit_type: Optional[str] = "其他事业单位"
    other_requirements: Optional[str] = ""
    announcement_title: Optional[str] = ""
    announcement_text: Optional[str] = ""

class BianzhiEvalResponse(BaseModel):
    is_bianzhi: int
    bianzhi_type: str
    bianzhi_confidence: float
    bianzhi_evidence: str

class BatchBianzhiResponse(BaseModel):
    status: str
    total_jobs: int
    green_bianzhi: int
    yellow_uncertain: int
    red_non_bianzhi: int
