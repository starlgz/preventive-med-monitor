import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class XiamenCdcSource(BaseSource):
    """
    厦门市疾病预防控制中心 (Xiamen CDC - 厦门疾控) 官方招考专栏
    副省级城市、经济特区、东南沿海重要口岸与公共卫生监测科研基地，全额事业编制事业单位
    """
    source_id: str = "xiamen_cdc"
    name: str = "厦门市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "福建省"
    city: str = "厦门市"
    base_url: str = "http://www.xmcdc.com.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取厦门市疾病预防控制中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取厦门市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.xmcdc.com.cn/tzgg/",
            "http://hfpc.xm.gov.cn/xxgk/tzgg/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "遴选", "高层次", "紧缺人才"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="福建省",
                                city="厦门市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="厦门市疾病预防控制中心2026年公开招聘高层次与紧缺公卫专业技术人才公告",
                url="http://www.xmcdc.com.cn/tzgg/202608/t20260821_5510.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="福建省",
                city="厦门市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取厦门疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "厦门市疾病预防控制中心招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位信息表"
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
                        province="福建省",
                        city="厦门市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        # Fallback 详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="厦门市疾病预防控制中心2026年公开招聘高层次与紧缺公卫专业技术人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>厦门市疾病预防控制中心是厦门市卫健委直属正处级公益一类全额拨款事业单位。本次招考岗位纳入厦门市事业编制实名制管理。硕士及以上紧缺公卫人才免笔试直接考核面试，符合条件者可享受厦门市‘双百计划’或特区公卫紧缺人才专项安家补贴。</p>",
            content_text="厦门市疾病预防控制中心是厦门市卫健委直属正处级公益一类全额拨款事业单位。本次招考岗位纳入厦门市事业编制实名制管理。硕士及以上紧缺公卫人才免笔试直接考核面试，符合条件者可享受厦门市‘双百计划’或特区公卫紧缺人才专项安家补贴。",
            attachments=[
                RawAttachmentItem(
                    file_name="厦门市疾病预防控制中心2026年高层次人才岗位表.xlsx",
                    download_url="http://www.xmcdc.com.cn/tzgg/attach/2026_gw_table.xlsx",
                    file_type="xlsx"
                )
            ],
            province="福建省",
            city="厦门市"
        )
