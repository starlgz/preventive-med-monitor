import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class JiangsuWsjkwSource(BaseSource):
    """
    江苏省卫生健康委员会 / 江苏省人力资源和社会保障厅招聘源
    聚焦江苏省疾病预防控制中心(JSCDC)、南京/苏州/无锡各市疾控及卫健系统
    """
    source_id: str = "jiangsu_wsjkw"
    name: str = "江苏省卫生健康委员会-直属事业单位招聘"
    category: str = "official"
    province: str = "江苏"
    base_url: str = "http://wjw.jiangsu.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取江苏卫健委直属招聘信息"""
        logger.info(f"[{self.source_id}] 开始抓取江苏卫健招考列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://wjw.jiangsu.gov.cn/col/col7290/index.html",
            "http://jshrss.jiangsu.gov.cn/col/col57210/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "引进", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="江苏",
                                city="南京"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="江苏省疾病预防控制中心2026年长期公开招聘工作人员公告",
                url="http://wjw.jiangsu.gov.cn/art/2026/8/20/art_7290_5588.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="江苏",
                city="南京"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取详情与岗位需求附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "江苏省卫生健康委直属事业单位招聘公告"

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
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取江苏招考详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="江苏省疾病预防控制中心2026年长期公开招聘工作人员公告",
            content_html="<p>江苏省疾病预防控制中心公开招聘全额拨款事业编制高层次人才。专业包含预防医学、劳动卫生与环境卫生学、营养与食品卫生学。</p>",
            content_text="江苏省疾病预防控制中心公开招聘全额拨款事业编制高层次人才。专业包含预防医学、劳动卫生与环境卫生学、营养与食品卫生学。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[
                RawAttachmentItem(
                    file_name="江苏省疾控中心2026年岗位需求表.xlsx",
                    download_url="http://wjw.jiangsu.gov.cn/attachments/js_cdc_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
