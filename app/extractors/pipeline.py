import re
import hashlib
from typing import Dict, Any, List
from app.extractors.unit_type_classifier import UnitTypeClassifier
from app.extractors.eligibility_extractor import EligibilityExtractor
from app.extractors.pitfall_extractor import PitfallExtractor

class ExtractionPipeline:
    """岗位清洗、画像丰富与标准化数据管道"""

    @classmethod
    def clean_text(cls, text: Any) -> str:
        if text is None:
            return ""
        s = str(text).strip()
        s = re.sub(r"\s+", " ", s)
        return s

    @classmethod
    def parse_headcount(cls, count_val: Any) -> int:
        if count_val is None:
            return 1
        s = str(count_val).strip()
        m = re.search(r"(\d+)", s)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return 1
        return 1

    @classmethod
    def generate_job_uid(cls, unit_name: str, job_code: str, job_name: str, education: str, major_raw: str) -> str:
        """生成岗位去重唯一 SHA256 识别码"""
        raw_str = f"{unit_name.strip()}|{job_code.strip()}|{job_name.strip()}|{education.strip()}|{major_raw.strip()}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    @classmethod
    def process_jobs(
        cls,
        raw_jobs: List[Dict[str, Any]],
        default_unit: str,
        announcement_title: str,
        source_province: str = "全国"
    ) -> List[Dict[str, Any]]:
        """批量清洗并补全四维画像、避坑研判与标准化字段"""
        processed = []
        for raw in raw_jobs:
            unit_name = cls.clean_text(raw.get("unit_name")) or default_unit
            job_name = cls.clean_text(raw.get("job_name"))
            if not job_name:
                continue

            job_code = cls.clean_text(raw.get("job_code"))
            headcount = cls.parse_headcount(raw.get("headcount"))
            education = cls.clean_text(raw.get("education")) or "不限"
            degree = cls.clean_text(raw.get("degree"))
            major_raw = cls.clean_text(raw.get("major_raw")) or cls.clean_text(raw.get("major"))
            other_req = cls.clean_text(raw.get("other_requirements")) or cls.clean_text(raw.get("notes")) or cls.clean_text(raw.get("remarks"))

            # 1. 归一化单位类型
            unit_type = UnitTypeClassifier.classify(unit_name)

            # 2. 提取报考画像四维特征 (证书、规培、应届、年龄、户籍)
            el_features = EligibilityExtractor.extract_all(
                major_text=major_raw,
                education_text=education,
                other_text=other_req,
                full_text=announcement_title
            )

            # 3. 避坑与隐形门槛研判 (最低服务年限、违约责任、党员限制)
            combined_context = f"{announcement_title} {job_name} {other_req} {major_raw}"
            pitfall_info = PitfallExtractor.analyze(combined_context)

            # 4. 计算岗位唯一 job_uid
            job_uid = cls.generate_job_uid(unit_name, job_code, job_name, education, major_raw)

            # 5. 构建标准化岗位字典
            job_dict = {
                "job_uid": job_uid,
                "unit_name": unit_name,
                "unit_type": unit_type,
                "province": source_province,
                "city": "市属/省属",
                "district": "",
                "job_name": job_name,
                "job_code": job_code,
                "headcount": headcount,
                "education": education,
                "degree": degree,
                "major_raw": major_raw,
                "cert_requirements": el_features["cert_requirements"],
                "is_training_required": el_features["is_training_required"],
                "is_fresh_grad": el_features["is_fresh_grad"],
                "age_limit_num": el_features["age_limit_num"],
                "residency_limit": el_features["residency_limit"],
                "experience_req": other_req,
                "notes": other_req,
                "pitfall_analysis": pitfall_info
            }
            processed.append(job_dict)

        return processed
