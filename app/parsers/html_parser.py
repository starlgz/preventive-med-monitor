import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from app.core.logger import logger
from app.parsers.html_table_parser import HtmlTableJobParser

class HtmlJobParser:
    """
    网页 HTML 正文与内嵌表格解析引擎
    """

    @classmethod
    def parse_html_tables(cls, html_content: str, default_unit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        提取 HTML 中直接渲染的 <table> 岗位数据
        """
        return HtmlTableJobParser.parse_html_tables(html_content, default_unit_name=default_unit_name)

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
