import docx
from typing import List, Dict, Any, Optional
from app.core.logger import logger
from app.parsers.column_mapper import ColumnMapper

class WordJobParser:
    """Word 文档 (.docx) 岗位表专用解析器"""

    @classmethod
    def parse_file(cls, file_path: str, default_unit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        jobs = []
        try:
            doc = docx.Document(file_path)
            for table in doc.tables:
                table_jobs = cls._parse_table(table, default_unit_name)
                jobs.extend(table_jobs)
        except Exception as e:
            logger.error(f"Error parsing word docx {file_path}: {e}")
        return jobs

    @classmethod
    def _parse_table(cls, table, default_unit_name: Optional[str]) -> List[Dict[str, Any]]:
        rows = table.rows
        if not rows:
            return []

        header_row_idx = -1
        col_map = {}
        for idx, row in enumerate(rows):
            row_vals = [cell.text.strip() for cell in row.cells]
            mapped = ColumnMapper.map_columns(row_vals)
            if "job_name" in mapped or "major" in mapped:
                header_row_idx = idx
                col_map = mapped
                break

        if header_row_idx == -1:
            return []

        jobs = []
        last_unit = default_unit_name or ""
        for r_idx in range(header_row_idx + 1, len(rows)):
            row = rows[r_idx]
            row_vals = [cell.text.strip() for cell in row.cells]
            if not any(row_vals):
                continue

            unit = row_vals[col_map["unit_name"]] if "unit_name" in col_map and col_map["unit_name"] < len(row_vals) else ""
            if unit:
                last_unit = unit
            else:
                unit = last_unit

            job_name = row_vals[col_map["job_name"]] if "job_name" in col_map and col_map["job_name"] < len(row_vals) else ""
            major_raw = row_vals[col_map["major"]] if "major" in col_map and col_map["major"] < len(row_vals) else ""
            job_code = row_vals[col_map["job_code"]] if "job_code" in col_map and col_map["job_code"] < len(row_vals) else ""
            headcount_raw = row_vals[col_map["headcount"]] if "headcount" in col_map and col_map["headcount"] < len(row_vals) else "1"
            education = row_vals[col_map["education"]] if "education" in col_map and col_map["education"] < len(row_vals) else ""
            other_req = row_vals[col_map["other_requirements"]] if "other_requirements" in col_map and col_map["other_requirements"] < len(row_vals) else ""

            if not job_name and not major_raw:
                continue

            try:
                headcount = int(float(headcount_raw)) if headcount_raw else 1
            except:
                headcount = 1

            jobs.append({
                "unit_name": unit or default_unit_name or "未指定招聘单位",
                "job_name": job_name or "未命名岗位",
                "job_code": job_code,
                "headcount": headcount,
                "education": education,
                "major_raw": major_raw,
                "other_requirements": other_req
            })
        return jobs
