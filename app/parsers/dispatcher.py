import os
import json
from typing import Dict, Any, List
from app.core.logger import logger
from app.parsers.html_cleaner import HtmlCleaner
from app.parsers.html_table_parser import HtmlTableJobParser
from app.parsers.excel_parser import ExcelJobParser
from app.parsers.word_parser import WordJobParser
from app.parsers.attachment_downloader import AttachmentDownloader

class ParserDispatcher:
    """解析总调度器：负责正文清洗、HTML表格提取、附件异步下载与解析"""

    @classmethod
    def parse_file(cls, file_path: str, default_unit_name: str = "") -> Dict[str, Any]:
        """按文件后缀分发解析单个本地附件"""
        import os
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".xlsx", ".xls"]:
            jobs = ExcelJobParser.parse_file(file_path, default_unit_name=default_unit_name)
            return {"status": "SUCCESS", "data": jobs}
        elif ext == ".docx":
            jobs = WordJobParser.parse_file(file_path, default_unit_name=default_unit_name)
            return {"status": "SUCCESS", "data": jobs}
        elif ext == ".pdf":
            from app.parsers.pdf_parser import PdfJobParser
            jobs = PdfJobParser.parse_pdf(file_path, default_unit_name=default_unit_name)
            return {"status": "SUCCESS", "data": jobs}
        return {"status": "FAILED", "data": [], "error": f"Unsupported ext {ext}"}

    @classmethod
    async def parse_announcement(cls, ann_id: int, title: str, raw_content: str, raw_attachments_json: str, unit_name: str = "") -> Dict[str, Any]:
        result = {
            "announcement_id": ann_id,
            "title": title,
            "clean_text": "",
            "clean_text_length": 0,
            "jobs_count": 0,
            "attachments": [],
            "raw_jobs": []
        }

        # 1. 正文清洗
        clean_text = HtmlCleaner.clean_html(raw_content)
        result["clean_text"] = clean_text
        result["clean_text_length"] = len(clean_text)

        all_jobs = []

        # 2. 解析 HTML 内嵌表格
        if "<table" in (raw_content or "").lower():
            try:
                html_jobs = HtmlTableJobParser.parse_html_tables(raw_content, default_unit_name=unit_name)
                all_jobs.extend(html_jobs)
            except Exception as e:
                logger.warning(f"Failed to parse HTML tables for ann {ann_id}: {e}")

        # 3. 解析附件
        att_list = []
        if raw_attachments_json:
            try:
                parsed_att_list = json.loads(raw_attachments_json)
                if isinstance(parsed_att_list, list):
                    att_list = parsed_att_list
            except:
                pass

        for att in att_list:
            att_name = att.get("file_name") or att.get("name", "")
            att_url = att.get("url", "")
            if not att_url:
                continue

            # 异步下载附件
            downloaded = await AttachmentDownloader.download_file(att_url, att_name)
            if not downloaded:
                continue

            local_path = downloaded.get("local_path", "")
            ext = downloaded.get("file_ext", "").lower()
            att_jobs = []

            if ext in [".xlsx", ".xls"]:
                att_jobs = ExcelJobParser.parse_file(local_path, default_unit_name=unit_name)
            elif ext == ".docx":
                att_jobs = WordJobParser.parse_file(local_path, default_unit_name=unit_name)

            all_jobs.extend(att_jobs)

            result["attachments"].append({
                "filename": att_name,
                "file_ext": ext,
                "file_size": downloaded.get("file_size", 0),
                "local_path": local_path,
                "jobs_extracted_count": len(att_jobs)
            })

        result["raw_jobs"] = all_jobs
        result["jobs_count"] = len(all_jobs)
        return result


# 别名兼容
AttachmentParserDispatcher = ParserDispatcher
