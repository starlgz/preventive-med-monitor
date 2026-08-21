import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from app.core.logger import logger
from app.parsers.excel_parser import ExcelJobParser

class HtmlJobParser:
    """
    网页 HTML 正文与内嵌表格解析引擎
    """

    @classmethod
    def parse_html_tables(cls, html_content: str) -> List[Dict[str, Any]]:
        """
        提取 HTML 中直接渲染的 <table> 岗位数据
        """
        results = []
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            tables = soup.find_all("table")
            
            for table in tables:
                all_rows = []
                for tr in table.find_all("tr"):
                    cells = tr.find_all(["td", "th"])
                    row_vals = [c.get_text(strip=True) for c in cells]
                    if any(row_vals):
                        all_rows.append(row_vals)

                if not all_rows:
                    continue

                header_row_idx, col_map = ExcelJobParser._detect_headers(all_rows)
                if header_row_idx == -1:
                    continue

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
            logger.error(f"Error parsing HTML tables: {e}")

        return results

    @classmethod
    def extract_clean_text(cls, html_content: str) -> str:
        """
        提取正文纯文本，去除 script, style 等无用标签
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)
        except Exception as e:
            logger.error(f"Error extracting HTML clean text: {e}")
            return ""
