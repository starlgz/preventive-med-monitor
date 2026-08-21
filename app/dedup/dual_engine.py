from typing import Dict, Any, List, Optional
from app.dedup.simhash import SimHashDedup
from app.rules.deduplicator import JobDeduplicator

class DualDeduplicationEngine:
    """
    双层去重与公告延期追踪引擎：
    1. 第一层：公告级 SimHash 文本指纹 + 海明距离 (识别延期/变更/重复抓取公告)
    2. 第二层：岗位级 SHA-256 结构化指纹 + 加权相似度算法 (跨平台岗位排重)
    """

    @classmethod
    def check_announcement_update(
        cls,
        old_title: str,
        old_content: str,
        new_title: str,
        new_content: str
    ) -> Dict[str, Any]:
        """公告层级变更与延期追踪"""
        return SimHashDedup.detect_announcement_change(
            old_title=old_title,
            old_text=old_content,
            new_title=new_title,
            new_text=new_content
        )

    @classmethod
    def check_job_duplicate(
        cls,
        job_a: Dict[str, Any],
        job_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """岗位层级跨平台去重比对"""
        is_dup, sim, reason = JobDeduplicator.is_duplicate_job(job_a, job_b)
        return {
            "is_duplicate": is_dup,
            "similarity": sim,
            "reason": reason
        }
