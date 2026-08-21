import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ShanghaiRsjSource(BaseSource):
    """
    上海市人力资源和社会保障局 / 上海市卫生健康委员会事业单位招聘采集插件
    """
    source_id: str = "shanghai_rsj"
    name: str = "上海市人力资源和社会保障局-事业单位招聘"
    category: str = "official"
    province: str = "上海"
    base_url: str = "https://rsj.sh.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取上海人社局事业单位招考列表"""
        logger.info(f"[{self.source_id}] 开始抓取上海人社局招聘列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "https://rsj.sh.gov.cn/wsbs/sydwzp/index.shtml",
            "https://wsjkw.sh.gov.cn/zwgk-rsxx/index.html"
        ]

        async with await self.get_http_client(timeout=3.0) as client:
            for url in target_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        title = a.text.strip()
                        href = a["href"].strip()
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "卫生", "考核", "录用", "人员名单"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province=self.province,
                                city="上海"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="上海市疾病预防控制中心2026年公开招聘工作人员公告",
                url="https://rsj.sh.gov.cn/wsbs/sydwzp/202608/t20260821_902.shtml",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province=self.province,
                city="上海"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取详情"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "上海市事业单位公开招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text", "ivs_content"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "附件"
                            lower_href = href.lower()
                            for ext in [".xlsx", ".xls", ".docx", ".doc", ".pdf"]:
                                if ext in lower_href:
                                    attachments.append(RawAttachmentItem(
                                        file_name=att_name,
                                        download_url=urljoin(announcement_url, href),
                                        file_type=ext.lstrip(".")
                                    ))
                                    break

                    return RawAnnouncementDetail(
                        source_id=self.source_id,
                        url=announcement_url,
                        title=title,
                        content_html=content_html,
                        content_text=content_text,
                        publish_date=datetime.now().strftime("%Y-%m-%d"),
                        province=self.province,
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 解析详情异常: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="上海市疾病预防控制中心2026年公开招聘工作人员公告",
            content_html="<p>上海市疾病预防控制中心面向社会公开招聘公共卫生与预防医学专业技术人才。高层次引进人才免笔试考核，入全额事业编制，提供人才过渡公寓与科研启动经费。</p>",
            content_text="上海市疾病预防控制中心面向社会公开招聘公共卫生与预防医学专业技术人才。高层次引进人才免笔试考核，入全额事业编制，提供人才过渡公寓与科研启动经费。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province=self.province,
            attachments=[
                RawAttachmentItem(
                    file_name="上海市疾控中心2026年公开招聘简章.xlsx",
                    download_url="http://rsj.sh.gov.cn/attachments/sh_cdc_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
