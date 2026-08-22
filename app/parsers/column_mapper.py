import re
from typing import List, Dict, Optional

class ColumnMapper:
    """智能表头模糊映射器：根据列名语义自动映射岗位字段"""

    EXCLUDE_PATTERNS = {
        "job_name": [r"类别", r"等级", r"性质", r"总表", r"汇总表", r"一览表", r"岗位表"],
        "job_code": [r"专业代码", r"专业及代码", r"专业与代码", r"所需专业与代码"],
        "major": [r"专业技术", r"技术等级"]
    }

    PATTERNS = {
        "unit_name": [
            r"招聘单位", r"用人单位", r"单位名称", r"申报单位", r"主管部门", r"工作单位", r"单位", r"部门名称"
        ],
        "job_name": [
            r"岗位名称", r"招考职位", r"职位名称", r"招聘岗位", r"拟聘岗位", r"岗位", r"职位"
        ],
        "job_code": [
            r"岗位代码", r"职位代码", r"岗位编号", r"职位编号", r"岗位序号", r"专业代码", r"代码"
        ],
        "headcount": [
            r"招聘人数", r"计划人数", r"招考人数", r"拟聘人数", r"录用人数", r"招聘计划", r"人数"
        ],
        "education": [
            r"学历要求", r"最低学历", r"学历学位", r"文化程度", r"学历"
        ],
        "major": [
            r"专业要求", r"专业及代码", r"专业与代码", r"所需专业与代码", r"所学专业", r"招考专业", r"所需专业", r"专业及方向", r"专业"
        ],
        "other_requirements": [
            r"其他资格条件", r"其他条件", r"报考条件", r"资格条件", r"招聘条件", r"其他要求", r"备注"
        ]
    }

    @classmethod
    def map_columns(cls, headers: List[str]) -> Dict[str, int]:
        mapping = {}
        for idx, header in enumerate(headers):
            if not header or not str(header).strip():
                continue
            cleaned = str(header).strip().replace("\n", "").replace(" ", "")

            # 按照优先级匹配
            matched_key = None
            for key, patterns in cls.PATTERNS.items():
                if key in mapping:
                    continue  # 已匹配的不再重复覆盖
                
                # 检查排除模式
                if key in cls.EXCLUDE_PATTERNS:
                    if any(re.search(ex, cleaned) for ex in cls.EXCLUDE_PATTERNS[key]):
                        continue

                for pat in patterns:
                    if re.search(pat, cleaned):
                        matched_key = key
                        break
                if matched_key:
                    mapping[matched_key] = idx
                    break
        return mapping
