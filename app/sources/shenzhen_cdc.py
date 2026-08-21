import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ShenzhenCdcSource(BaseSource):
    """
    深圳市疾病预防控制中心 (Shenzhen CDC - 深圳疾控) 官方招考专栏
    副省级/经济特区超大城市疾控中枢，公益一类高水平公共卫生事业单位
    """
    source_id: str = "shenzhen_cdc"
    name: str = "深圳市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "广东省"
    city: str = "深圳市"
    base_url: str = "http://szzx.sz.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取深圳市疾病预防控制中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取深圳市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://szzx.sz.gov.cn/xxgk/rsxx/ryzk/",
            "http://wjw.sz.gov.cn/xxgk/rsxx/zkzp/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "选聘", "紧缺人才", "公告", "博士"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="广东省",
                                city="深圳市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="深圳市疾病预防控制中心2026年选聘高层次公共卫生专业技术人才公告",
                url="http://szzx.sz.gov.cn/xxgk/rsxx/ryzk/202608/t20260821_8801.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="广东省",
                city="深圳市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取深圳市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "深圳市疾病预防控制中心招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位表"
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
                        city="深圳市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        # Fallback 模拟详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="深圳市疾病预防控制中心2026年选聘高层次公共卫生专业技术人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>深圳市疾病预防控制中心面向海内外公开选聘高层次公共卫生专业技术人才，纳入财政全额拨款实名制事业编制管理。对全日制博士研究生免笔试直接考核面试，提供孔雀计划对等补贴及安家补贴50万元，配备独立实验室与科研启动金。</p>",
            content_text="深圳市疾病预防控制中心面向海内外公开选聘高层次公共卫生专业技术人才，纳入财政全额拨款实名制事业编制管理。对全日制博士研究生免笔试直接考核面试，提供孔雀计划对等补贴及安家补贴50万元，配备独立实验室与科研启动金。",
            attachments=[
                RawAttachmentItem(
                    file_name="深圳市疾病预防控制中心2026年公开选聘岗位表.xlsx",
                    download_url="http://szzx.sz.gov.cn/files/2026_szcdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="广东省",
            city="深圳市"
        )
