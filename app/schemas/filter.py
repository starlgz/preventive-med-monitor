from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserFilterCreate(BaseModel):
    user_id: str
    channel: str = "telegram"
    filter_name: str = "默认订阅条件"
    provinces: Optional[List[str]] = []
    min_star: int = 3
    only_bianzhi: bool = False
    include_beian: bool = True
    education_level: Optional[str] = None
    is_fresh_grad: Optional[bool] = None
    has_cert: Optional[bool] = None
    max_age: Optional[int] = None
    unit_types: Optional[List[str]] = []
    is_active: bool = True

class UserFilterResponse(BaseModel):
    id: int
    user_id: str
    channel: str
    filter_name: str
    filter_rules: Dict[str, Any]
    is_active: bool
    created_at: datetime

class FilterMatchRequest(BaseModel):
    user_id: str
    job_id: int

class FilterMatchResponse(BaseModel):
    user_id: str
    job_id: int
    matched: bool
    reason: str
