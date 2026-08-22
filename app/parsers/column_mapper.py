import re
from typing import List, Dict, Optional, Tuple

class ColumnMapper:
    """智能表头模糊映射器 2.0：支持多级复合表头语义合成与高精度列映射"""

    # 绝对排除模式（命中则拒绝映射为此字段）
    EXCLUDE_PATTERNS = {
        "job_name": [
            r"类别", r"等级", r"性质", r"总表", r"汇总表", r"一览表", r"岗位表", r"计划表",
            r"序号", r"编号", r"代码", r"专业代码", r"笔试", r"面试", r"备注", r"单位名称",
            r"主管部门", r"用人单位", r"招聘单位", r"学历", r"学位", r"专业要求"
        ],
        "job_code": [
            r"专业代码", r"专业及代码", r"专业与代码", r"所需专业与代码", r"专业名称"
        ],
        "major": [
            r"专业技术", r"技术等级", r"专业类别", r"岗位类别"
        ],
        "unit_name": [
            r"岗位名称", r"职位名称", r"拟聘岗位"
        ]
    }

    # 优先级匹配模式（越靠前优先级越高）
    PATTERNS = {
        "unit_name": [
            r"招聘单位", r"用人单位", r"单位名称", r"用人科室", r"用人部门", r"用工单位", r"招考单位", r"申报单位", r"主管部门", r"工作单位", r"设岗单位", r"部门名称", r"^部门$", r"^单位$"
        ],
        "job_name": [
            r"岗位名称", r"招考职位", r"职位名称", r"招聘岗位", r"拟聘岗位", r"招考岗位", r"招聘职位", r"用人岗位", r"^岗位$", r"^职位$"
        ],
        "job_code": [
            r"岗位代码", r"职位代码", r"岗位编号", r"职位编号", r"岗位序号", r"职位序号", r"招聘代码", r"^代码$"
        ],
        "headcount": [
            r"招聘人数", r"计划人数", r"招考人数", r"拟聘人数", r"录用人数", r"招录计划", r"招聘计划", r"拟招人数", r"招录人数", r"招考计划", r"计划数", r"招聘名额", r"^人数$"
        ],
        "education": [
            r"学历要求", r"最低学历学位", r"学历学位要求", r"学历及学位要求", r"最低学历", r"学历学位", r"文化程度", r"学历/学位", r"学历及学位", r"学历"
        ],
        "degree": [
            r"学位要求", r"最低学位", r"^学位$"
        ],
        "major": [
            r"专业要求及代码", r"专业名称及代码", r"所需专业与代码", r"所需专业及代码", r"专业及代码", r"专业与代码", r"专业条件", r"专业要求", r"所学专业", r"招考专业", r"所需专业", r"专业及方向", r"报考专业", r"专业限制", r"^专业$"
        ],
        "age": [
            r"年龄要求", r"年龄上限", r"出生年月", r"^年龄$"
        ],
        "employment_type": [
            r"编制类型", r"用工性质", r"用工形式", r"经费形式", r"岗位性质", r"编制情况", r"编制"
        ],
        "other_requirements": [
            r"其他资格条件", r"其他条件", r"报考条件", r"资格条件", r"招聘条件", r"其他要求", r"准考条件", r"备注", r"其他说明"
        ]
    }

    @classmethod
    def clean_text(cls, text: any) -> str:
        if text is None:
            return ""
        return str(text).strip().replace("\n", "").replace("\r", "").replace(" ", "")

    @classmethod
    def map_columns(cls, headers: List[str]) -> Dict[str, int]:
        """单行表头映射"""
        mapping: Dict[str, int] = {}
        cleaned_headers = [cls.clean_text(h) for h in headers]

        # 遍历所有目标字段
        for key, patterns in cls.PATTERNS.items():
            best_idx = -1
            best_priority = 999

            for idx, h_text in enumerate(cleaned_headers):
                if not h_text or idx in mapping.values():
                    continue

                # 检查排除模式
                if key in cls.EXCLUDE_PATTERNS:
                    if any(re.search(ex, h_text) for ex in cls.EXCLUDE_PATTERNS[key]):
                        continue

                # 匹配模式优先级
                for p_idx, pat in enumerate(patterns):
                    if re.search(pat, h_text):
                        if p_idx < best_priority:
                            best_priority = p_idx
                            best_idx = idx
                        break

            if best_idx != -1:
                mapping[key] = best_idx

        return mapping

    @classmethod
    def synthesize_multi_headers(cls, header_rows: List[List[str]]) -> List[str]:
        """将多行表头自底向上合成为扁平化的复合表头"""
        if not header_rows:
            return []
        if len(header_rows) == 1:
            return [cls.clean_text(h) for h in header_rows[0]]

        num_cols = max(len(row) for row in header_rows)
        synthesized = []

        for c in range(num_cols):
            col_parts = []
            for r in range(len(header_rows)):
                if c < len(header_rows[r]):
                    val = cls.clean_text(header_rows[r][c])
                    if val and val not in col_parts:
                        col_parts.append(val)
            synthesized.append("_".join(col_parts))

        return synthesized

    @classmethod
    def evaluate_header_score(cls, row_cells: List[str]) -> int:
        """评估一行像表头的得分（包含核心关键词越多得分越高）"""
        score = 0
        cleaned = [cls.clean_text(c) for c in row_cells]
        core_keywords = ["岗位", "职位", "专业", "学历", "人数", "单位", "代码", "条件", "要求", "备注"]
        
        for text in cleaned:
            if not text:
                continue
            for kw in core_keywords:
                if kw in text:
                    score += 2
            if text in ["序号", "单位", "岗位", "专业", "学历", "人数"]:
                score += 3
        return score
