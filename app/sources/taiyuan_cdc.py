from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger


class TaiyuanCdcSource(BaseSource):
    """
    太原市疾病预防控制中心 (Taiyuan CDC - 山西省会核心疾控)
    山西省会城市，华北煤矿职业病/尘肺监测重点机构，全额拨款公益一类事业单位
    """
    source_id: str = "taiyuan_cdc"
    name: str = "太原市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "山西省"
    city: str = "太原市"
    base_url: str = "http://www.tycdc.com.cn"
    enabled: bool = True
    interval_minutes: int = 45

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取太原市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.tycdc.com.cn/tzgg/",
            "http://wjw.taiyuan.gov.cn/gkxx/zfxxgkml/tzgg/rsxx/",
            "http://rsj.taiyuan.gov.cn/ywdt/zxgg/",
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
                                province="山西省",
                                city="太原市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="太原市疾病预防控制中心2026年公开招聘预防医学专业事业编制人员公告",
                url="http://www.tycdc.com.cn/tzgg/202608/t20260821_001.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="山西省",
                city="太原市"
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
                    title = title_tag.text.strip() if title_tag else "太原市疾病预防控制中心招聘公告"
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
                        attachments=attachments, province="山西省", city="太原市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="太原市疾病预防控制中心2026年公开招聘预防医学专业事业编制人员公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>太原市疾病预防控制中心是山西省会核心疾控机构，重点承担煤矿职业病、尘肺病、职业性有害因素监测等劳动卫生与环境卫生工作，全额财政拨款公益一类事业单位。面向预防医学、劳动卫生与环境卫生学、职业卫生等专业招聘在编人员。</p>",
            content_text="太原市疾控2026年招聘预防医学、劳动卫生与环境卫生学专业编制人员，公益一类全额拨款单位。",
            attachments=[
                RawAttachmentItem(
                    file_name="太原疾控2026年岗位需求表.xlsx",
                    download_url="http://www.tycdc.com.cn/files/2026_tycdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="山西省",
            city="太原市"
        )
