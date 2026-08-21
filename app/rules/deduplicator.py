import re
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple, Optional

class JobDeduplicator:
    """
    多源跨平台岗位相似度去重与合并引擎
    - 解决聚合网站（如中公、华图、粉笔）与官方源（如各省人社厅、卫健委）发布同一岗位时的跨源重复问题
    - 单位名称同义词归一化（疾控中心/疾病预防控制中心、卫健委/卫生健康委员会等）
    - 岗位名称同义词归一化、关键业务词提纯与重合度算法
    - 支持识别岗位状态变更（new: 新增 / updated_deadline: 截止时间延期 / repost: 重新发布）
    """

    @staticmethod
    def normalize_unit_name(text: Optional[str]) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"[\s\(\)\[\]（）_—\-,，。]", "", text)
        cleaned = re.sub(r"(公开|统一|选聘|面向社会|招聘|招录|事业单位|工作人员|公告|简章|关于|年度|202[0-9]年?)", "", cleaned)
        
        # 常见同义词与单位简称归一化
        cleaned = cleaned.replace("疾病预防控制中心", "疾控中心")
        cleaned = cleaned.replace("预防控制中心", "疾控中心")
        cleaned = cleaned.replace("卫生健康委员会", "卫健委")
        cleaned = cleaned.replace("卫生健康局", "卫健局")
        cleaned = cleaned.replace("妇幼保健计划生育服务中心", "妇幼保健院")
        cleaned = cleaned.replace("卫生监督所", "卫监所")
        cleaned = cleaned.replace("卫生监督局", "卫监局")
        return cleaned.lower()

    @staticmethod
    def normalize_job_name(text: Optional[str]) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"[\s\(\)\[\]（）_—\-,，。]", "", text)
        # 去除末尾的修饰词
        cleaned = re.sub(r"(岗位|岗|人员|人员招聘)$", "", cleaned)
        # 去除通用业务修饰词
        cleaned = re.sub(r"(突发公共卫生事件|突发公共事件|公共卫生|专技|专业技术|专技岗|专职|业务|科员|公卫医师|公卫)", "", cleaned)
        return cleaned.lower()

    @classmethod
    def calculate_similarity(cls, str1: str, str2: str, mode: str = "unit") -> float:
        if not str1 or not str2:
            return 0.0
        n1 = cls.normalize_unit_name(str1) if mode == "unit" else cls.normalize_job_name(str1)
        n2 = cls.normalize_unit_name(str2) if mode == "unit" else cls.normalize_job_name(str2)
        
        if n1 == n2 or (n1 and n1 == n2):
            return 1.0
        
        # 若清洗后为空（如全部是修饰词），退回原字符相似度
        if not n1 or not n2:
            raw1 = re.sub(r"[\s\(\)\[\]（）_—\-,，。]", "", str1).lower()
            raw2 = re.sub(r"[\s\(\)\[\]（）_—\-,，。]", "", str2).lower()
            return SequenceMatcher(None, raw1, raw2).ratio()

        # 包含关系
        if n1 in n2 or n2 in n1:
            overlap = min(len(n1), len(n2)) / max(len(n1), len(n2))
            if overlap >= 0.5:
                return max(0.90, overlap)

        return SequenceMatcher(None, n1, n2).ratio()

    @classmethod
    def is_duplicate_job(
        cls,
        job_a: Dict[str, Any],
        job_b: Dict[str, Any],
        unit_threshold: float = 0.80,
        job_threshold: float = 0.70
    ) -> Tuple[bool, float, str]:
        """
        判断两个岗位是否为跨源同一岗位
        """
        # 1. 相同省份或城市（如果不为空）
        prov_a = job_a.get("province", "")
        prov_b = job_b.get("province", "")
        if prov_a and prov_b and prov_a != prov_b:
            return False, 0.0, "省份不匹配"

        # 2. 单位相似度
        unit_sim = cls.calculate_similarity(job_a.get("unit_name", ""), job_b.get("unit_name", ""), mode="unit")
        if unit_sim < unit_threshold:
            return False, unit_sim, f"单位名称相似度过低 ({unit_sim:.2f} < {unit_threshold})"

        # 3. 岗位名称相似度
        job_sim = cls.calculate_similarity(job_a.get("job_name", ""), job_b.get("job_name", ""), mode="job")
        if job_sim < job_threshold:
            return False, job_sim, f"岗位名称相似度过低 ({job_sim:.2f} < {job_threshold})"

        # 4. 专业或学历重合检查
        edu_a = job_a.get("education", "")
        edu_b = job_b.get("education", "")
        edu_sim = 1.0 if (not edu_a or not edu_b or edu_a == edu_b) else 0.7

        total_sim = 0.5 * unit_sim + 0.35 * job_sim + 0.15 * edu_sim
        if total_sim >= 0.75:
            return True, total_sim, f"多源同一岗位 (综合相似度: {total_sim:.2f})"

        return False, total_sim, f"综合相似度不足 ({total_sim:.2f} < 0.75)"
