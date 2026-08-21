import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.entities import Announcement, Attachment
from app.parsers.dispatcher import ParserDispatcher
from app.schemas.parser import AnnouncementParseResponse

router = APIRouter(prefix="/parsers", tags=["公告与附件解析器"])

@router.post("/parse_announcement/{announcement_id}", response_model=AnnouncementParseResponse)
async def parse_announcement(announcement_id: int, db: AsyncSession = Depends(get_db)):
    """解析指定公告的正文及附件岗位表"""
    stmt = select(Announcement).where(Announcement.id == announcement_id)
    res = await db.execute(stmt)
    ann = res.scalar_one_or_none()

    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # 查询已有的附件关联记录
    att_stmt = select(Attachment).where(Attachment.announcement_id == announcement_id)
    att_res = await db.execute(att_stmt)
    existing_atts = att_res.scalars().all()

    attachment_urls = []
    if existing_atts:
        for att in existing_atts:
            if att.file_url:
                attachment_urls.append(att.file_url)

    parsed_result = await ParserDispatcher.parse_announcement(
        announcement_id=ann.id,
        title=ann.title,
        content_html=ann.content_raw or "",
        attachment_urls=attachment_urls
    )

    return parsed_result
