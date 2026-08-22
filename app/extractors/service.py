import os
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import Announcement, Job, Attachment
from app.parsers.dispatcher import AttachmentParserDispatcher
from app.extractors.pipeline import ExtractionPipeline
from app.core.logger import logger

class JobExtractionService:
    """从公告（正文/表格/附件）提取并结构化入库岗位数据服务"""

    @classmethod
    async def extract_and_save_jobs(cls, db: AsyncSession, announcement_id: int) -> Dict[str, Any]:
        # 1. 查找公告详情
        stmt = select(Announcement).where(Announcement.id == announcement_id)
        res = await db.execute(stmt)
        ann = res.scalar_one_or_none()
        if not ann:
            logger.error(f"Announcement {announcement_id} not found.")
            return {"status": "FAILED", "reason": "Announcement not found"}

        # 2. 收集原始岗位（优先附件，其次正文/HTML表格）
        raw_jobs = []

        # 检查是否有已保存的附件（不强制要求 parse_status == "success"）
        att_stmt = select(Attachment).where(
            Attachment.announcement_id == announcement_id
        )
        attachments = (await db.execute(att_stmt)).scalars().all()

        for att in attachments:
            if att.local_path and os.path.exists(att.local_path):
                parsed_res = AttachmentParserDispatcher.parse_file(att.local_path)
                if parsed_res.get("status") == "SUCCESS":
                    att.parse_status = "success"
                    for row in parsed_res.get("data", []):
                        raw_jobs.append(row)
                else:
                    att.parse_status = "failed"

        # 若附件无数据，则从公告 HTML 正文提取表格
        if not raw_jobs and ann.content_raw:
            from app.parsers.html_table_parser import HtmlTableParser
            html_table_jobs = HtmlTableParser.extract_jobs_from_html(ann.content_raw)
            if html_table_jobs:
                raw_jobs.extend(html_table_jobs)

        if not raw_jobs:
            logger.info(f"No jobs extracted for announcement {announcement_id}")
            return {
                "status": "SUCCESS",
                "announcement_id": announcement_id,
                "title": ann.title,
                "total_extracted": 0,
                "new_saved": 0,
                "updated": 0,
                "jobs_summary": []
            }

        # 3. 运行清洗与四维特征提取管道
        src_province = "全国"
        if getattr(ann, "province", None) and ann.province != "全国":
            src_province = ann.province
        elif getattr(ann, "source", None) and getattr(ann.source, "province", None):
            src_province = ann.source.province
        else:
            # 从标题推断省份
            _province_map = {
                "北京": "北京", "上海": "上海", "天津": "天津", "重庆": "重庆",
                "广东": "广东", "浙江": "浙江", "江苏": "江苏", "山东": "山东",
                "四川": "四川", "湖北": "湖北", "湖南": "湖南", "河南": "河南",
                "陕西": "陕西", "福建": "福建", "安徽": "安徽", "河北": "河北",
                "辽宁": "辽宁", "吉林": "吉林", "黑龙江": "黑龙江", "云南": "云南",
                "贵州": "贵州", "广西": "广西", "新疆": "新疆", "西藏": "西藏",
                "内蒙古": "内蒙古", "宁夏": "宁夏", "甘肃": "甘肃", "青海": "青海",
                "海南": "海南", "山西": "山西", "江西": "江西"
            }
            title_text = (ann.title or "") + (ann.content_raw or "")[:200]
            for prov_key, prov_val in _province_map.items():
                if prov_key in title_text:
                    src_province = prov_val
                    break

        structured_jobs = ExtractionPipeline.process_jobs(
            raw_jobs=raw_jobs,
            default_unit=ann.title.split("公开招聘")[0] if "公开招聘" in ann.title else "招考单位",
            announcement_title=ann.title,
            source_province=src_province
        )

        # 4. 写入/更新 jobs 表 (根据 job_uid 严格排重)
        new_count = 0
        updated_count = 0
        summary_list = []

        for job_data in structured_jobs:
            uid = job_data["job_uid"]
            
            # 查询是否存在相同 job_uid
            existing_stmt = select(Job).where(Job.job_uid == uid)
            existing_job = (await db.execute(existing_stmt)).scalar_one_or_none()

            # 严格对齐 Job ORM 实体字段
            job_dict = {
                "announcement_id": ann.id,
                "job_uid": uid,
                "unit_name": job_data["unit_name"],
                "unit_type": job_data["unit_type"],
                "job_code": job_data.get("job_code"),
                "job_name": job_data["job_name"],
                "headcount": job_data.get("headcount", 1),
                "education": job_data.get("education", "本科及以上"),
                "degree": job_data.get("degree"),
                "major_raw": job_data.get("major_raw", ""),
                "cert_requirements": job_data.get("cert_requirements"),
                "is_training_required": job_data.get("is_training_required", 0),
                "is_fresh_grad": job_data.get("is_fresh_grad", 0),
                "age_limit_num": job_data.get("age_limit_num"),
                "residency_limit": job_data.get("residency_limit"),
                "province": job_data.get("province") or src_province,
                "city": job_data.get("city")
            }

            if existing_job:
                # 更新已有岗位
                for k, v in job_dict.items():
                    if k not in ["id", "created_at"]:
                        setattr(existing_job, k, v)
                updated_count += 1
                summary_list.append({"job_uid": uid, "job_name": job_data["job_name"], "action": "UPDATED"})
            else:
                # 新增岗位
                new_job = Job(**job_dict)
                db.add(new_job)
                new_count += 1
                summary_list.append({"job_uid": uid, "job_name": job_data["job_name"], "action": "CREATED"})

        await db.commit()
        logger.info(f"Announcement {announcement_id} extracted {len(raw_jobs)} jobs. Saved: {new_count}, Updated: {updated_count}")

        return {
            "status": "SUCCESS",
            "announcement_id": announcement_id,
            "title": ann.title,
            "total_extracted": len(raw_jobs),
            "new_saved": new_count,
            "updated": updated_count,
            "jobs_summary": summary_list
        }
