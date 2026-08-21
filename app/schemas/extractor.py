from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class JobItemSummary(BaseModel):
    unit_name: str
    unit_type: str
    job_name: str
    headcount: int
    education: str
    cert_requirements: str
    is_fresh_grad: int

class ExtractJobsResponse(BaseModel):
    status: str
    announcement_id: int
    title: str
    total_extracted: int
    new_saved: int
    updated: int
    jobs_summary: List[JobItemSummary]
