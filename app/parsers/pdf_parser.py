import re
from typing import List, Dict, Any, Optional
import pdfplumber
from app.core.logger import logger
from app.parsers.excel_parser import ExcelJobParser

class PdfJobParser:
    """
    PDF 公告与岗位表解析引擎
    支持：
    1. PDF 内部表格提取并映射标准岗位结构
    2. PDF 纯文本提取 (用于后续正文与编制依据分析)
    """

    @classmethod
    def parse_pdf_tables(cls, file_path: str) -> List[Dict[str, Any]]:
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

                # 复用 Excel 表头检测与映射逻辑
                header_row_idx, col_map = ExcelJobParser._detect_headers(all_rows)
                if header_row_idx == -1:
                    logger.warning(f"No valid table header detected in PDF: {file_path}")
                    return []

                last_unit_name = ""
                for r_idx in range(header_row_idx + 1, len(all_rows)):
                    row_vals = all_rows[r_idx]
                    item = ExcelJobParser._extract_row_data(row_vals, col_map)
                    
                    if item.get("unit_name"):
                        last_unit_name = item["unit_name"]
                    elif last_unit_name and item.get("job_name"):
                        item["unit_name"] = last_unit_name

                    if item.get("job_name") or item.get("major"):
                        results.append(item)

        except Exception as e:
            logger.error(f"Error parsing PDF tables from {file_path}: {e}")

        return results

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
