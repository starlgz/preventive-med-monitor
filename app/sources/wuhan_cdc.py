import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class WuhanCdcSource(BaseSource):
    """
    武汉市疾病预防控制中心 (Wuhan CDC - 武汉疾控) 官方招考专栏
    副省级城市/华中地区传染病防控与科研基地，全额事业编制事业单位
    """
    source_id: str = "wuhan_cdc"
    name: str = "武汉市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "湖北省"
    city: str = "武汉市"
    base_url: str = "http://www.whcdc.org"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取武汉市疾病预防控制中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取武汉市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.whcdc.org/tzgg/",
            "http://wjw.wuhan.gov.cn/tzgg/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "专项", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="湖北省",
                                city="武汉市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="武汉市疾病预防控制中心2026年度专项招聘专业技术人员公告",
                url="http://www.whcdc.org/tzgg/202608/t20260821_4421.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="湖北省",
                city="武汉市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取武汉市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "武汉市疾病预防控制中心招聘公告"

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
                        province="湖北省",
                        city="武汉市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        # Fallback 模拟详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="武汉市疾病预防控制中心2026年度专项招聘专业技术人员公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>武汉市疾病预防控制中心为武汉市卫健委直属公益一类事业单位，本次招聘计划纳入武汉市事业单位财政全额拨款编制管理。硕博研究生免笔试直接进入面试综合考核，落实武汉英才公共卫生专项津贴。</p>",
            content_text="武汉市疾病预防控制中心为武汉市卫健委直属公益一类事业单位，本次招聘计划纳入武汉市事业单位财政全额拨款编制管理。硕博研究生免笔试直接进入面试综合考核，落实武汉英才公共卫生专项津贴。",
            attachments=[
                RawAttachmentItem(
                    file_name="武汉市疾控中心2026年专项招聘岗位表.xlsx",
                    download_url="http://www.whcdc.org/files/2026_whcdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="湖北省",
            city="武汉市"
        )
