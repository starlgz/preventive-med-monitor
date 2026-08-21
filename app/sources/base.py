import abc
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl
import httpx
from app.core.logger import logger

class RawAttachmentItem(BaseModel):
    """附件元数据模型"""
    file_name: str
    download_url: str
    file_type: Optional[str] = None  # xlsx, xls, doc, docx, pdf, zip 等

class RawAnnouncementItem(BaseModel):
    """抓取到的原始公告条目模型"""
    source_id: str                   # 对应数据源 ID
    title: str                       # 原始标题
    url: str                         # 详情页 URL
    publish_date: Optional[str] = None  # 格式: YYYY-MM-DD
    province: Optional[str] = None   # 归属省份
    city: Optional[str] = None       # 归属城市
    extra_meta: Optional[Dict[str, Any]] = None

class RawAnnouncementDetail(BaseModel):
    """原始公告详情模型"""
    source_id: str
    url: str
    title: str
    content_html: str                # 原始 HTML
    content_text: str                # 清洗后的纯文本
    publish_date: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    attachments: List[RawAttachmentItem] = []
    crawl_time: datetime = datetime.now()

class BaseSource(abc.ABC):
    """
    所有招聘数据源插件的统一基类 (契约规范)
    """
    source_id: str             # 唯一标识符，如 "chinagwy_wszp"
    name: str                  # 插件可读名称，如 "全国事业单位招聘网-医疗卫生"
    category: str              # aggregate (聚合) / official (官方人社/疾控) / search (通用搜索)
    province: Optional[str] = "全国"
    base_url: str
    driver_type: str = "http"  # http / playwright
    enabled: bool = True       # 默认是否启用
    interval_minutes: int = 30 # 建议轮询间隔

    def __init__(self):
        # 通用请求头，模拟真实浏览器
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    async def get_http_client(self, timeout: float = 3.0) -> httpx.AsyncClient:
        """获取标准异步 HTTP 客户端 (默认3秒超时，防止爬虫挂起阻塞)"""
        return httpx.AsyncClient(
            headers=self.headers,
            timeout=timeout,
            follow_redirects=True,
            verify=False  # 兼容部分政府网站过期证书
        )

    @abc.abstractmethod
    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """
        获取最新公告列表 (由具体插件实现)
        :param max_pages: 抓取页数 (增量调度通常为 1~2 页)
        :return: 原始公告简要列表
        """
        pass

    @abc.abstractmethod
    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """
        获取单篇公告正文和附件列表 (由具体插件实现)
        :param announcement_url: 公告详情页 URL
        :return: 详细结构化数据 (正文、纯文本、附件列表)
        """
        pass

    def __repr__(self) -> str:
        return f"<SourcePlugin id={self.source_id} name='{self.name}' enabled={self.enabled}>"
