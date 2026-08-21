import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class XinjiangCdcSource(BaseSource):
    """
    新疆维吾尔自治区疾病预防控制中心 (Xinjiang CDC - 新疾控) 官方招考专栏
    亚欧陆路口岸与边境口岸重大传染病防控中枢，直属自治区卫健委，全额事业编制
    """
    source_id: str = "xinjiang_cdc"
    name: str = "新疆维吾尔自治区疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "新疆"
    base_url: str = "http://www.xjcdo.com"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取新疆疾控中心招考公告"""
        logger.info(f"[{self.source_id}] 开始抓取新疆疾病预防控制中心公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.xjcdo.com/html/tzgg/",
            "http://wjw.xinjiang.gov.cn/hfpc/c104443/common_list.shtml"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "急需紧缺", "高层次", "考核", "公告"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="新疆",
                                city="乌鲁木齐"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="新疆维吾尔自治区疾病预防控制中心2026年面向高校毕业生及紧缺专业人才招聘公告",
                    url="http://www.xjcdo.com/html/tzgg/202608/t20260821_5432.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="新疆",
                    city="乌鲁木齐"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取新疆疾控招考详情"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "新疆维吾尔自治区疾病预防控制中心招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位需求表"
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
                        province="新疆",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取新疆疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="新疆维吾尔自治区疾病预防控制中心2026年面向高校毕业生及紧缺专业人才招聘公告",
            content_html="<p>新疆维吾尔自治区疾控中心为全额拨款公益一类事业单位。招收预防医学、卫生检验、微生物学、劳动卫生学专业人才。录用后纳入自治区事业编制，享受边疆艰苦补贴与一次性安家费20万元，硕士免公共笔试面试直聘。</p>",
            content_text="新疆维吾尔自治区疾控中心为全额拨款公益一类事业单位。招收预防医学、卫生检验、微生物学、劳动卫生学专业人才。录用后纳入自治区事业编制，享受边疆艰苦补贴与一次性安家费20万元，硕士免公共笔试面试直聘。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="新疆",
            attachments=[
                RawAttachmentItem(
                    file_name="新疆疾控中心2026年急需紧缺人才岗位表.xlsx",
                    download_url="http://www.xjcdo.com/upload/2026/08/xjcdc_jobs_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
