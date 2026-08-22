import os
import re
import hashlib
import httpx
import aiofiles
import shutil
from typing import Optional, Dict, Any
from app.core.logger import logger

class AttachmentDownloader:
    """附件下载与本地缓存管理器"""
    ATTACHMENT_DIR = "data/attachments"

    @classmethod
    def clean_filename(cls, filename: str) -> str:
        """清理文件名中的文件大小后缀，例如 '岗位表.xls (37.5 KB)' -> '岗位表.xls'"""
        if not filename:
            return ""
        cleaned = re.sub(r'[\(\[\s]*\d+(\.\d+)?\s*(KB|MB|Bytes|B)[\)\]\s]*$', '', filename, flags=re.IGNORECASE).strip()
        return cleaned

    @classmethod
    def detect_extension_from_magic(cls, content: bytes) -> Optional[str]:
        """根据文件二进制文件头（Magic Number）精准判断真实扩展名"""
        if len(content) < 8:
            return None
        # PK\x03\x04 -> Zip 容器 (xlsx, docx, zip)
        if content[:4] == b"PK\x03\x04":
            return ".xlsx"
        # \xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1 -> OLE2 (xls, doc)
        if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return ".xls"
        # %PDF- -> PDF
        if content[:5] == b"%PDF-":
            return ".pdf"
        return None

    @classmethod
    def get_file_extension(cls, url: str, content_type: Optional[str] = None, original_filename: Optional[str] = None) -> str:
        cleaned_name = cls.clean_filename(original_filename) if original_filename else ""
        if cleaned_name:
            fn_lower = cleaned_name.lower()
            for ext in [".xlsx", ".xls", ".docx", ".doc", ".pdf", ".zip", ".rar", ".7z", ".csv", ".txt"]:
                if fn_lower.endswith(ext):
                    return ext

        url_lower = url.split("?")[0].lower()
        for ext in [".xlsx", ".xls", ".docx", ".doc", ".pdf", ".zip", ".rar", ".7z", ".csv", ".txt"]:
            if url_lower.endswith(ext):
                return ext
        if content_type:
            ct = content_type.lower()
            if "spreadsheetml" in ct or "excel" in ct:
                return ".xlsx"
            if "wordprocessingml" in ct or "msword" in ct:
                return ".docx"
            if "pdf" in ct:
                return ".pdf"
            if "zip" in ct:
                return ".zip"
        return ".bin"

    @classmethod
    async def download_file(cls, url: str, original_filename: str = "") -> Optional[Dict[str, Any]]:
        """下载远程附件或复制本地 file:// 附件并缓存至本地"""
        try:
            os.makedirs(cls.ATTACHMENT_DIR, exist_ok=True)
            cleaned_filename = cls.clean_filename(original_filename)
            
            # 支持本地测试 file:// 协议
            if url.startswith("file://"):
                local_src = url.replace("file://", "")
                if os.path.exists(local_src):
                    with open(local_src, "rb") as f:
                        content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()
                    ext = cls.detect_extension_from_magic(content) or os.path.splitext(local_src)[1].lower()
                    target_filename = f"{file_hash[:16]}_{cleaned_filename or os.path.basename(local_src)}"
                    if not target_filename.endswith(ext):
                        target_filename += ext
                    dest_path = os.path.join(cls.ATTACHMENT_DIR, target_filename)
                    shutil.copyfile(local_src, dest_path)
                    return {
                        "local_path": dest_path,
                        "file_size": len(content),
                        "file_ext": ext,
                        "sha256": file_hash,
                        "filename": cleaned_filename or os.path.basename(local_src)
                    }
                else:
                    logger.error(f"Local file not found: {local_src}")
                    return None

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"Failed to download attachment from {url}: status {response.status_code}")
                    return None

                content = response.content
                file_size = len(content)
                file_hash = hashlib.sha256(content).hexdigest()
                content_type = response.headers.get("Content-Type", "")
                
                # 优先从文件魔数精准判定，其次从清理后的文件名推导
                magic_ext = cls.detect_extension_from_magic(content)
                name_ext = cls.get_file_extension(url, content_type, cleaned_filename)
                
                # 如果是 doc/docx 或 xls/xlsx，利用 magic_ext 做二选一修正
                if name_ext in [".xls", ".xlsx"]:
                    ext = ".xlsx" if magic_ext == ".xlsx" else ".xls"
                elif name_ext in [".doc", ".docx"]:
                    ext = ".docx" if magic_ext == ".xlsx" else ".doc"
                else:
                    ext = magic_ext or name_ext
                
                safe_name = "".join(c for c in cleaned_filename if c.isalnum() or c in "._- ") if cleaned_filename else ""
                target_filename = f"{file_hash[:16]}_{safe_name or 'attachment'}"
                if not target_filename.endswith(ext):
                    target_filename += ext

                dest_path = os.path.join(cls.ATTACHMENT_DIR, target_filename)
                async with aiofiles.open(dest_path, "wb") as f:
                    await f.write(content)

                logger.info(f"Attachment saved: {dest_path} ({file_size} bytes)")
                return {
                    "local_path": dest_path,
                    "file_size": file_size,
                    "file_ext": ext,
                    "sha256": file_hash,
                    "filename": cleaned_filename or target_filename
                }
        except Exception as e:
            logger.error(f"Error downloading attachment from {url}: {e}")
            return None
