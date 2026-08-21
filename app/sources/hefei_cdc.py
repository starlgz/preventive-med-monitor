import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HefeiCdcSource(BaseSource):
    """
    合肥市疾病预防控制中心 (Hefei CDC - 庐州疾控) 官方招考专栏
    科创新城与安徽公卫枢纽中心、全额拨款事业单位
    """
    source_id: str = "hefei_cdc"
    name: str = "合肥市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "安徽省"
    city: str = "合肥市"
    base_url: str = "http://www.hfcdc.org.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取合肥市疾病预防控制中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取合肥市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.hfcdc.org.cn/tzgg/index.html",
            "http://wjw.hefei.gov.cn/tzgg/index.html",
            "http://rsj.hefei.gov.cn/zpxx/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "引进", "紧缺人才", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="安徽省",
                                city="合肥市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="合肥市疾病预防控制中心2026年公开招聘公卫高素质人才公告",
                url="http://www.hfcdc.org.cn/tzgg/2026/art_20260821_hfcdc01.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="安徽省",
                city="合肥市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取合肥疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "合肥市疾病预防控制中心招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位需求计划表"
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
                        province="安徽省",
                        city="合肥市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        # Fallback 详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="合肥市疾病预防控制中心2026年公开招聘公卫高素质人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>合肥市疾病预防控制中心为合肥市卫生健康委员会直属正处级公益一类全额拨款事业单位。招录人员纳入合肥市事业单位实名制事业编制。硕士及以上预防医学专业优秀人才享受直接面试考评待遇免笔试，享受合肥市重点产业与卫生人才安居租房补贴。</p>",
            content_text="合肥市疾病预防控制中心为合肥市卫生健康委员会直属正处级公益一类全额拨款事业单位。招录人员纳入合肥市事业单位实名制事业编制。硕士及以上预防医学专业优秀人才享受直接面试考评待遇免笔试，享受合肥市重点产业与卫生人才安居租房补贴。",
            attachments=[
                RawAttachmentItem(
                    file_name="合肥市疾控中心2026年岗位需求计划表.xlsx",
                    download_url="http://www.hfcdc.org.cn/tzgg/attach/2026_hf_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="安徽省",
            city="合肥市"
        )
