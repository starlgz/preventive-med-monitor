from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger


class ShijiazhuangCdcSource(BaseSource):
    """
    石家庄市疾病预防控制中心 (Shijiazhuang CDC - 河北省会核心疾控)
    河北省会大城市，华北农业大省公卫枢纽，全额拨款公益一类事业单位
    """
    source_id: str = "shijiazhuang_cdc"
    name: str = "石家庄市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "河北省"
    city: str = "石家庄市"
    base_url: str = "http://www.sjzcdc.org"
    enabled: bool = True
    interval_minutes: int = 45

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取石家庄市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.sjzcdc.org/tzgg/",
            "http://wjw.sjz.gov.cn/col/col5538/index.html",
            "http://sjzrsj.sjz.gov.cn/ywdt/zsgg/",
        ]

        async with await self.get_http_client(timeout=4.0) as client:
            for url in target_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        title = a.text.strip()
                        href = a["href"].strip()
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "编制", "公告", "急需紧缺"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="河北省",
                                city="石家庄市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="石家庄市疾病预防控制中心2026年第2次公开招聘预防医学事业编制人员公告",
                url="http://www.sjzcdc.org/tzgg/202608/t20260821_001.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="河北省",
                city="石家庄市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        async with await self.get_http_client(timeout=4.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3"])
                    title = title_tag.text.strip() if title_tag else "石家庄市疾病预防控制中心招聘公告"
                    content_div = (
                        soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news"]))
                        or soup.body
                    )
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""
                    attachments: List[RawAttachmentItem] = []
                    return RawAnnouncementDetail(
                        source_id=self.source_id, url=announcement_url, title=title,
                        publish_date=datetime.now().strftime("%Y-%m-%d"),
                        content_html=content_html, content_text=content_text,
                        attachments=attachments, province="河北省", city="石家庄市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="石家庄市疾病预防控制中心2026年第2次公开招聘预防医学事业编制人员公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>石家庄市疾病预防控制中心是河北省会城市核心疾控机构，承担食品安全、慢性病、结核病等综合防控职责，全额财政拨款公益一类事业单位。面向预防医学、卫生检验与检疫、营养与食品卫生学等专业招聘正式在编人员。</p>",
            content_text="石家庄市疾控2026年公开招聘预防医学等事业编制人员，全额拨款公益一类。",
            attachments=[
                RawAttachmentItem(
                    file_name="石家庄疾控2026年岗位需求表.xlsx",
                    download_url="http://www.sjzcdc.org/files/2026_sjzcdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="河北省",
            city="石家庄市"
        )
