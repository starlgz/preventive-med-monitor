from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from app.parsers.column_mapper import ColumnMapper

class HtmlTableJobParser:
    """HTML 内嵌 <table> 岗位表格解析器"""

    @classmethod
    def parse_html_tables(cls, html_content: str, default_unit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        if not html_content or "<table" not in html_content.lower():
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        tables = soup.find_all("table")
        jobs = []

        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue

            header_row_idx = -1
            col_map = {}

            # 寻找表头
            for idx, row in enumerate(rows):
                cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                mapped = ColumnMapper.map_columns(cells)
                if "job_name" in mapped or "major" in mapped:
                    header_row_idx = idx
                    col_map = mapped
                    break

            if header_row_idx == -1:
                continue

            last_unit = default_unit_name or ""
            for r_idx in range(header_row_idx + 1, len(rows)):
                cells = [c.get_text(strip=True) for c in rows[r_idx].find_all(["th", "td"])]
                if not any(cells):
                    continue

                unit = cells[col_map["unit_name"]] if "unit_name" in col_map and col_map["unit_name"] < len(cells) else ""
                job_name = cells[col_map["job_name"]] if "job_name" in col_map and col_map["job_name"] < len(cells) else ""
                major_raw = cells[col_map["major"]] if "major" in col_map and col_map["major"] < len(cells) else ""
                job_code = cells[col_map["job_code"]] if "job_code" in col_map and col_map["job_code"] < len(cells) else ""
                headcount_raw = cells[col_map["headcount"]] if "headcount" in col_map and col_map["headcount"] < len(cells) else "1"
                education = cells[col_map["education"]] if "education" in col_map and col_map["education"] < len(cells) else ""
                other_req = cells[col_map["other_requirements"]] if "other_requirements" in col_map and col_map["other_requirements"] < len(cells) else ""

                # 过滤汇总/统计行
                import re
                if re.match(r"^(合计|总计|小计|共计)", job_name.strip()) or (re.match(r"^(合计|总计|小计|共计)", unit.strip()) and not major_raw):
                    continue

                if unit:
                    last_unit = unit
                else:
                    unit = last_unit

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

    @classmethod
    def extract_jobs_from_html(cls, html_content: str, default_unit_name: str = None) -> list:
        """alias for backward compat"""
        return cls.parse_html_tables(html_content, default_unit_name=default_unit_name)

HtmlTableParser = HtmlTableJobParser  # backward compat alias
