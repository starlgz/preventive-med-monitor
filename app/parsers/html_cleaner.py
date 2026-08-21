import re
from bs4 import BeautifulSoup

class HtmlCleaner:
    """HTML 正文清洗器：剔除无关标签、样式脚本、多余空白，保留纯文本与段落结构"""

    @classmethod
    def clean_html(cls, raw_html: str) -> str:
        if not raw_html or not raw_html.strip():
            return ""

        soup = BeautifulSoup(raw_html, "html.parser")

        # 剔除无关干扰标签
        for tag in soup(["script", "style", "header", "footer", "nav", "aside", "noscript", "svg"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        # 清理多余空行与空格
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
