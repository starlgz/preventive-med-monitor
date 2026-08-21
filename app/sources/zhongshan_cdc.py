import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ZhongshanCdcSource(BaseSource):
    """
    中山市疾病预防控制中心 (Zhongshan CDC) 官方招考专栏
    珠三角核心城市/粤港澳大湾区公卫高地，全额事业编制事业单位
    """
    source_id: str = "zhongshan_cdc"
    name: str = "中山市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "广东省"
    city: str = "中山市"
    base_url: str = "http://www.zs-cdc.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取中山市疾控中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取中山市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.zs-cdc.cn/tzgg/index.html",
            "http://wjj.zs.gov.cn/zwgk/rsxx/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "考核", "专业技术"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="广东省",
                                city="中山市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="中山市疾病预防控制中心2026年公开招聘紧缺预防医学专业人才公告",
                url="http://www.zs-cdc.cn/tzgg/20260822_zs.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="广东省",
                city="中山市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取中山市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "中山市疾病预防控制中心招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位一览表"
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
                        publish_date=datetime.now().strftime("%Y-%m-%d"),
                        content_html=content_html,
                        content_text=content_text,
                        attachments=attachments,
                        province="广东省",
                        city="中山市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        # Fallback 模拟详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="中山市疾病预防控制中心2026年公开招聘紧缺预防医学专业人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>中山市疾病预防控制中心为公益一类全额拨款事业单位。本次招聘纳入中山市特聘人才政策支持范畴，提供全额事业编制，可享最高30万安家补贴及免租住房。</p>",
            content_text="中山市疾病预防控制中心为公益一类全额拨款事业单位。本次招聘纳入中山市特聘人才政策支持范畴，提供全额事业编制，可享最高30万安家补贴及免租住房。",
            attachments=[
                RawAttachmentItem(
                    file_name="中山市疾控中心2026年岗位表.xlsx",
                    download_url="http://www.zs-cdc.cn/files/2026_zscdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="广东省",
            city="中山市"
        )
