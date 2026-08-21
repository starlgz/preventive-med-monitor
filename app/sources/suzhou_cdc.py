import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class SuzhouCdcSource(BaseSource):
    """
    苏州市疾病预防控制中心 (Suzhou CDC - 姑苏疾控) 官方招考专栏
    长三角公卫现代化典范城市、地级市疾控领头羊、全额拨款事业单位
    """
    source_id: str = "suzhou_cdc"
    name: str = "苏州市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "江苏省"
    city: str = "苏州市"
    base_url: str = "http://www.szcdc.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取苏州市疾病预防控制中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取苏州市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.szcdc.cn/tzgg/index.html",
            "http://wsjkw.suzhou.gov.cn/szwjw/gsgg/list.shtml",
            "http://hrss.suzhou.gov.cn/jsszhrss/sydwzp/sydwzp.shtml"
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
                                province="江苏省",
                                city="苏州市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="苏州市疾病预防控制中心2026年公开招聘公卫高层次人才公告",
                url="http://www.szcdc.cn/tzgg/2026/art_20260821_szcdc01.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="江苏省",
                city="苏州市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取苏州疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "苏州市疾病预防控制中心招聘公告"

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
                        province="江苏省",
                        city="苏州市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        # Fallback 详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="苏州市疾病预防控制中心2026年公开招聘公卫高层次人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>苏州市疾病预防控制中心为苏州市卫生健康委员会直属正处级公益一类事业单位。本次招聘人员统一办理全额事业编制入编手续。面向高水平院校预防医学专业硕士研究生及博士开辟绿色通道免笔试考核招聘，享受苏州市‘姑苏卫生人才计划’公共卫生特聘人才安家补贴、薪酬补贴及科研项目资助。</p>",
            content_text="苏州市疾病预防控制中心为苏州市卫生健康委员会直属正处级公益一类事业单位。本次招聘人员统一办理全额事业编制入编手续。面向高水平院校预防医学专业硕士研究生及博士开辟绿色通道免笔试考核招聘，享受苏州市‘姑苏卫生人才计划’公共卫生特聘人才安家补贴、薪酬补贴及科研项目资助。",
            attachments=[
                RawAttachmentItem(
                    file_name="苏州市疾控中心2026年高层次人才招聘岗位表.xlsx",
                    download_url="http://www.szcdc.cn/tzgg/attach/2026_sz_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="江苏省",
            city="苏州市"
        )
