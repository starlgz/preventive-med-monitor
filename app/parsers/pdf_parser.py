import re
from typing import List, Dict, Any, Optional
import pdfplumber
from app.core.logger import logger
from app.parsers.column_mapper import ColumnMapper

class PdfJobParser:
    """
    PDF 公告与岗位表解析引擎
    支持：
    1. PDF 内部表格提取并映射标准岗位结构 (基于智能 ColumnMapper)
    2. PDF 纯文本提取 (用于正文与编制依据分析)
    """

    @classmethod
    def parse_pdf_tables(cls, file_path: str, default_unit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        提取 PDF 中排版的岗位表格
        """
        results = []
        try:
            with pdfplumber.open(file_path) as pdf:
                all_rows = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row and any(cell is not None and str(cell).strip() != "" for cell in row):
                                clean_row = [str(c).replace("\n", " ").strip() if c is not None else "" for c in row]
                                all_rows.append(clean_row)

                if not all_rows:
                    return []

                # 寻找最高分表头行
                best_score = 0
                best_header_idx = -1
                best_col_map = {}

                for idx, row in enumerate(all_rows[:15]):
                    score = ColumnMapper.evaluate_header_score(row)
                    col_map = ColumnMapper.map_columns(row)
                    if ("job_name" in col_map or "major" in col_map) and score > best_score:
                        best_score = score
                        best_header_idx = idx
                        best_col_map = col_map

                if best_header_idx == -1:
                    logger.warning(f"No valid table header detected in PDF: {file_path}")
                    return []

                last_unit_name = default_unit_name or ""
                summary_pattern = re.compile(r"^(合计|总计|小计|共计)")

                for r_idx in range(best_header_idx + 1, len(all_rows)):
                    row_vals = all_rows[r_idx]
                    if not any(row_vals):
                        continue

                    unit_name = row_vals[best_col_map["unit_name"]] if "unit_name" in best_col_map and best_col_map["unit_name"] < len(row_vals) else ""
                    job_name = row_vals[best_col_map["job_name"]] if "job_name" in best_col_map and best_col_map["job_name"] < len(row_vals) else ""
                    job_code = row_vals[best_col_map["job_code"]] if "job_code" in best_col_map and best_col_map["job_code"] < len(row_vals) else ""
                    major_raw = row_vals[best_col_map["major"]] if "major" in best_col_map and best_col_map["major"] < len(row_vals) else ""
                    education = row_vals[best_col_map["education"]] if "education" in best_col_map and best_col_map["education"] < len(row_vals) else ""
                    headcount_raw = row_vals[best_col_map["headcount"]] if "headcount" in best_col_map and best_col_map["headcount"] < len(row_vals) else "1"
                    other_req = row_vals[best_col_map["other_requirements"]] if "other_requirements" in best_col_map and best_col_map["other_requirements"] < len(row_vals) else ""

                    # 过滤汇总/统计行
                    if summary_pattern.match(job_name.strip()) or (summary_pattern.match(unit_name.strip()) and not major_raw):
                        continue

                    # 跨行合并向下继承 unit_name
                    if unit_name:
                        last_unit_name = unit_name
                    else:
                        unit_name = last_unit_name

                    if not job_name and not major_raw:
                        continue

                    try:
                        headcount = int(float(re.sub(r"[^\d.]", "", headcount_raw))) if headcount_raw else 1
                    except Exception:
                        headcount = 1

                    results.append({
                        "unit_name": unit_name or default_unit_name or "未指定招聘单位",
                        "job_name": job_name or "未命名岗位",
                        "job_code": job_code,
                        "headcount": headcount,
                        "education": education,
                        "major_raw": major_raw,
                        "other_requirements": other_req
                    })

        except Exception as e:
            logger.error(f"Error parsing PDF tables from {file_path}: {e}")

        return results

    @classmethod
    def parse_pdf(cls, file_path: str, default_unit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """别名兼容接口"""
        return cls.parse_pdf_tables(file_path, default_unit_name=default_unit_name)

    @classmethod
    def parse_file(cls, file_path: str, default_unit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """统一文件解析入口"""
        return cls.parse_pdf_tables(file_path, default_unit_name=default_unit_name)

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        """
        提取 PDF 全文文本
        """
        text_parts = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        except Exception as e:
            logger.error(f"Error extracting PDF text from {file_path}: {e}")
            
        return "\n".join(text_parts)
