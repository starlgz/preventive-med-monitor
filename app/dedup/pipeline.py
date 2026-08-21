from typing import Dict, Any, Tuple
from app.dedup.simhash import SimHashDedup
from app.extractors.pipeline import ExtractionPipeline
from app.rules.deduplicator import JobDeduplicator

class DualLayerDeduplicator:
    """
    双层公告与岗位去重引擎：
    1. 第一层：公告级 SimHash 文本指纹与海明距离检测（识别完全重复 / 延期修改更新 / 变更通知）
    2. 第二层：岗位级 SHA-256 唯一指纹 + 跨多源模糊相似度加权匹配
    """
    @classmethod
    def check_announcement(cls, old_simhash: int, new_text: str) -> dict:
        """公告层 SimHash 比对"""
        return SimHashDedup.is_content_changed(old_simhash, new_text)

    @classmethod
    def compute_job_uid(cls, job_data: Dict[str, Any]) -> str:
        """岗位层 SHA-256 唯一指纹"""
        return ExtractionPipeline.compute_job_uid(
            unit_name=job_data.get("unit_name", ""),
            job_code=job_data.get("job_code", ""),
            job_name=job_data.get("job_name", ""),
            education=job_data.get("education", ""),
            major_raw=job_data.get("major_raw", "")
        )

    @classmethod
    def match_cross_source_jobs(cls, job_a: Dict[str, Any], job_b: Dict[str, Any]) -> Tuple[bool, float, str]:
        """跨多源跨平台岗位相似度研判"""
        return JobDeduplicator.is_duplicate_job(job_a, job_b)
