import re
from typing import Dict, Any

class EligibilityExtractor:
    """报考门槛四维画像特征提取器"""

    @classmethod
    def extract_all(cls, major_text: str = "", education_text: str = "", other_text: str = "", full_text: str = "") -> Dict[str, Any]:
        combined = f"{major_text} {education_text} {other_text} {full_text}"
        return cls.extract_profile(other_requirements=combined)


    @classmethod
    def extract_profile(cls, other_requirements: str = "", job_name: str = "") -> Dict[str, Any]:
        text = f"{other_requirements or ''} {job_name or ''}"

        # 1. 证书要求 (公卫医师、临床医师、检验师、规培证等)
        certs = []
        if re.search(r"公共卫生执业医师|公卫执业医师|公卫医师", text):
            certs.append("公共卫生执业医师")
        if re.search(r"执业医师资格|执业医师证|具有医师资格", text) and not re.search(r"公卫", text):
            certs.append("执业医师资格")
        if re.search(r"临床执业医师", text):
            certs.append("临床执业医师")
        if re.search(r"检验技师|微生物检验|理化检验", text):
            certs.append("检验技师/专业资格")

        cert_str = "、".join(certs) if certs else "无明确证书限制"

        # 2. 规培要求
        is_training = 1 if re.search(r"规培|住院医师规范化培训|规范化培训合格", text) else 0

        # 3. 应届生要求 (1: 限应届, 2: 限往届/有工作经验, 0: 不限)
        is_fresh = 0
        if re.search(r"限应届|2026届|2025届|应届毕业生|高校应届毕业生", text):
            is_fresh = 1
        elif re.search(r"具有.*工作经历|年及以上工作经历|往届生|有.*经验", text):
            is_fresh = 2

        # 4. 年龄上限提取 (如 35周岁及以下 -> 35)
        age_limit = None
        age_match = re.search(r"(\d{2})\s*周岁(及以下|以下)", text)
        if age_match:
            age_limit = int(age_match.group(1))

        # 5. 户籍/生源限制
        residency = "全国不限"
        res_match = re.search(r"(限|要求|需).*?(户籍|生源|本地)", text)
        if res_match:
            residency = res_match.group(0)

        return {
            "cert_requirements": cert_str,
            "is_training_required": is_training,
            "is_fresh_grad": is_fresh,
            "age_limit_num": age_limit,
            "residency_limit": residency,
        }
