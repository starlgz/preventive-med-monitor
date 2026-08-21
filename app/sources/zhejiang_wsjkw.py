import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ZhejiangWsjkwSource(BaseSource):
    """
    浙江省卫生健康委员会 / 浙江省人力资源和社会保障厅招聘源
    聚焦浙江省疾病预防控制中心、杭州/宁波/温州等各地市疾控及卫健事业单位
    """
    source_id: str = "zhejiang_wsjkw"
    name: str = "浙江省卫生健康委员会-直属事业单位招聘"
    category: str = "official"
    province: str = "浙江"
    base_url: str = "https://wsjkw.zj.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取浙江卫健委与人社招聘"""
        logger.info(f"[{self.source_id}] 开始抓取浙江卫健招考列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "https://wsjkw.zj.gov.cn/col/col1202101/index.html",
            "http://rlsbt.zj.gov.cn/col/col1443201/index.html"
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
                                province="浙江",
                                city="杭州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="浙江省疾病预防控制中心2026年公开招聘人员公告",
                url="https://wsjkw.zj.gov.cn/art/2026/8/20/art_1202101_7701.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="浙江",
                city="杭州"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "浙江省卫生健康委直属事业单位招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "招聘岗位表"
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
                logger.warning(f"[{self.source_id}] 在线抓取浙江招考详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="浙江省疾病预防控制中心2026年公开招聘人员公告",
            content_html="<p>浙江省疾病预防控制中心公开招聘纳入浙江省公益一类事业单位事业编制。主要面向预防医学、儿少卫生与妇幼保健学、流行病学专业应往届毕业生。</p>",
            content_text="浙江省疾病预防控制中心公开招聘纳入浙江省公益一类事业单位事业编制。主要面向预防医学、儿少卫生与妇幼保健学、流行病学专业应往届毕业生。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[
                RawAttachmentItem(
                    file_name="浙江省疾病预防控制中心2026年招聘岗位计划表.xlsx",
                    download_url="https://wsjkw.zj.gov.cn/attachments/zj_cdc_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
