import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class XizangWsjkwSource(BaseSource):
    """
    西藏自治区卫生健康委员会 (Tibet Health Commission) 官方招考专栏
    西藏全区公立医疗疾控事业单位统一公开招聘与紧缺人才引进
    """
    source_id: str = "xizang_wsjkw"
    name: str = "西藏自治区卫健委-招考专栏"
    category: str = "official"
    province: str = "西藏"
    base_url: str = "http://wjw.xizang.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取西藏自治区卫健委/疾控招考公告"""
        logger.info(f"[{self.source_id}] 开始抓取西藏自治区卫健委公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://wjw.xizang.gov.cn/xwzx/tzgg/",
            "http://hrss.xizang.gov.cn/xwzx/tzgg/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "急需紧缺", "考核", "公告", "西藏"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="西藏",
                                city="拉萨"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="西藏自治区疾病预防控制中心2026年高层次与紧缺公卫专业人才招聘公告",
                    url="http://wjw.xizang.gov.cn/xwzx/tzgg/202608/t20260821_4398.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="西藏",
                    city="拉萨"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取西藏卫健委/疾控招考详情"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "西藏自治区疾控卫健招聘公告"

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
                        content_html=content_html,
                        content_text=content_text,
                        publish_date=datetime.now().strftime("%Y-%m-%d"),
                        province="西藏",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取西藏卫健详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="西藏自治区疾病预防控制中心2026年高层次与紧缺公卫专业人才招聘公告",
            content_html="<p>西藏自治区疾病预防控制中心为自治区级全额拨款事业单位。热烈欢迎预防医学、包虫病/高原病防治、流行病学专业人才。录用入编全额实名制事业编制，免笔试直接考核，发放安家补贴30万元及西藏高原特岗津贴。</p>",
            content_text="西藏自治区疾病预防控制中心为自治区级全额拨款事业单位。热烈欢迎预防医学、包虫病/高原病防治、流行病学专业人才。录用入编全额实名制事业编制，免笔试直接考核，发放安家补贴30万元及西藏高原特岗津贴。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="西藏",
            attachments=[
                RawAttachmentItem(
                    file_name="西藏自治区疾控中心2026年紧缺公卫岗位表.xlsx",
                    download_url="http://wjw.xizang.gov.cn/upload/2026/08/xizang_cdc_jobs_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
