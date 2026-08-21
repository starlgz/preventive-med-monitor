import re
from typing import Dict, Any, Optional

class JobProfiler:
    """四维画像提取器：从岗位要求与备注中提取学历/学位、应届、年龄上限、执业证书、规培、户籍要求等"""

    @classmethod
    def extract_education(cls, text: str) -> Dict[str, Any]:
        """提取学历与学位要求"""
        text = text or ""
        edu = "不限"
        degree = "不限"

        if re.search(r"博士", text):
            edu = "博士研究生"
            degree = "博士学位"
        elif re.search(r"硕士|研究生", text):
            edu = "硕士研究生"
            degree = "硕士学位"
        elif re.search(r"本科|学士|大学", text):
            edu = "本科及以上"
            degree = "学士学位"
        elif re.search(r"大专|专科", text):
            edu = "大专及以上"

        return {"education": edu, "degree": degree}

    @classmethod
    def extract_fresh_grad(cls, text: str) -> int:
        """判断是否限应届生：1-限应届, 0-不限, 2-限往届/有经验"""
        text = text or ""
        if re.search(r"仅限应届|限应届|2026届|应届毕业生", text):
            return 1
        if re.search(r"要求工作经历|年及以上工作经验|往届", text):
            return 2
        return 0

    @classmethod
    def extract_age_limit(cls, text: str) -> Dict[str, Any]:
        """提取年龄限制，数值化上限"""
        text = text or ""
        # 匹配 35周岁及以下, 30周岁以下, 35岁以下
        m = re.search(r"(\d{2})\s*(?:周岁|岁)\s*(?:及|以)?(?:下|内)", text)
        if m:
            age = int(m.group(1))
            return {"age_raw": f"{age}周岁及以下", "age_num": age}
        return {"age_raw": "不限", "age_num": None}

    @classmethod
    def extract_cert_requirements(cls, text: str) -> Dict[str, Any]:
        """提取证书门槛：公卫医师/规培/职称"""
        text = text or ""
        certs = []
        is_training_required = 0

        if re.search(r"公共卫生医师|公卫医师|公卫执业医师", text):
            certs.append("公共卫生执业医师")
        if re.search(r"执业医师|医师资格", text):
            if "公共卫生执业医师" not in certs:
                certs.append("执业医师资格")
        if re.search(r"规培|住院医师规范化培训|公共卫生医师规范化培训", text):
            certs.append("规培合格证")
            is_training_required = 1

        return {
            "cert_requirements": "、".join(certs) if certs else "无证书硬性限制",
            "is_training_required": is_training_required
        }

    @classmethod
    def extract_residency(cls, text: str) -> str:
        """提取户籍/生源地要求"""
        text = text or ""
        m = re.search(r"(限[^\s，,；;。]+(?:户籍|生源))", text)
        if m:
            return m.group(1)
        if re.search(r"本市户籍|本地户籍|本省户籍", text):
            return "限本地户籍"
        return "全国不限"
