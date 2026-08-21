import os
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
    def get_file_extension(cls, url: str, content_type: Optional[str] = None) -> str:
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
            
            # 支持本地测试 file:// 协议
            if url.startswith("file://"):
                local_src = url.replace("file://", "")
                if os.path.exists(local_src):
                    with open(local_src, "rb") as f:
                        content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()
                    ext = os.path.splitext(local_src)[1].lower()
                    target_filename = f"{file_hash[:16]}_{original_filename or os.path.basename(local_src)}"
                    if not target_filename.endswith(ext):
                        target_filename += ext
                    dest_path = os.path.join(cls.ATTACHMENT_DIR, target_filename)
                    shutil.copyfile(local_src, dest_path)
                    return {
                        "local_path": dest_path,
                        "file_size": len(content),
                        "file_ext": ext,
                        "sha256": file_hash,
                        "filename": original_filename or os.path.basename(local_src)
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
                ext = cls.get_file_extension(url, content_type)
                
                safe_name = "".join(c for c in original_filename if c.isalnum() or c in "._- ") if original_filename else ""
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
                    "filename": original_filename or target_filename
                }
        except Exception as e:
            logger.error(f"Error downloading attachment from {url}: {e}")
            return None
