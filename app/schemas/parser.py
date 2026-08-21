from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class AttachmentInfo(BaseModel):
    filename: str
    file_ext: str
    file_size: int
    local_path: str
    jobs_extracted_count: int

class AnnouncementParseResponse(BaseModel):
    announcement_id: int
    title: str
    clean_text_length: int
    jobs_count: int
    attachments: List[AttachmentInfo]
    raw_jobs: List[Dict[str, Any]]
