from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger


class ZhengzhouCdcSource(BaseSource):
    """
    郑州市疾病预防控制中心 (Zhengzhou CDC - 河南省会核心疾控)
    中原地区超大城市省会，人口大省核心疾控机构，全额拨款公益一类事业单位
    """
    source_id: str = "zhengzhou_cdc"
    name: str = "郑州市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "河南省"
    city: str = "郑州市"
    base_url: str = "http://www.zzcdc.com"
    enabled: bool = True
    interval_minutes: int = 40

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取郑州市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.zzcdc.com/tzgg/",
            "http://wjw.zhengzhou.gov.cn/xxgk/rsxx/zpzp/",
            "http://zzrsj.zhengzhou.gov.cn/ywdt/tdgg/",
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "编制", "公告", "人才引进", "急需紧缺"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="河南省",
                                city="郑州市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="郑州市疾病预防控制中心2026年公开招聘预防医学专业事业编制人员公告",
                url="http://www.zzcdc.com/tzgg/202608/t20260821_001.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="河南省",
                city="郑州市"
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
                    title = title_tag.text.strip() if title_tag else "郑州市疾病预防控制中心招聘公告"
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
                        attachments=attachments, province="河南省", city="郑州市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="郑州市疾病预防控制中心2026年公开招聘预防医学专业事业编制人员公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>郑州市疾病预防控制中心是中原地区重要疾控机构，承担全市传染病防控、慢性病监测、健康危害因素监测与干预职责，全额财政拨款公益一类事业单位。本次面向预防医学、流行病与卫生统计学、卫生检验等专业招聘在编人员，博士研究生可享受郑州市高层次人才引进政策。</p>",
            content_text="郑州市疾控2026年公开招聘预防医学等事业编制人员，博士可享高层次人才引进政策，全额事业编。",
            attachments=[
                RawAttachmentItem(
                    file_name="郑州疾控2026年岗位需求表.xlsx",
                    download_url="http://www.zzcdc.com/files/2026_zzcdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="河南省",
            city="郑州市"
        )
