import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ShiyebianSource(BaseSource):
    """
    全国事业单位招聘网 (shiyebian.com) - 医疗卫生/疾控公卫专栏数据源
    """
    source_id: str = "shiyebian_national"
    name: str = "事业单位招聘网-全国医疗公卫"
    category: str = "aggregator"
    province: str = "全国"
    base_url: str = "https://www.shiyebian.com"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取首页及医疗卫生频道的最新招聘公告"""
        logger.info(f"[{self.source_id}] 开始从 shiyebian.com 采集最新公告列表...")
        items: List[RawAnnouncementItem] = []
        seen_urls = set()

        channels = [
            "https://www.shiyebian.com/yiliaoweisheng/",
            "https://www.shiyebian.com/"
        ]

        async with await self.get_http_client(timeout=3.0) as client:
            for channel_url in channels:
                try:
                    resp = await client.get(channel_url)
                    if resp.status_code != 200:
                        logger.warning(f"[{self.source_id}] 请求栏目失败 {channel_url}: HTTP {resp.status_code}")
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        title = a.text.strip()

                        # 筛选详情页链接 (格式通常为 /xinxi/43459.html 或完整 URL)
                        if "/xinxi/" in href and re.search(r"/xinxi/\d+\.html", href):
                            full_url = urljoin(self.base_url, href)
                            if full_url in seen_urls:
                                continue
                            seen_urls.add(full_url)

                            # 医疗、卫生、疾控、医学等关键词优先采集，或纳入全量招聘
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="全国",
                                city="全国"
                            ))
                except Exception as e:
                    logger.error(f"[{self.source_id}] 抓取频道异常 {channel_url}: {e}")

        logger.info(f"[{self.source_id}] 成功获取到 {len(items)} 条候选招聘公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取并解析公告详情页正文与附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code != 200:
                    logger.warning(f"[{self.source_id}] 抓取详情页失败 {announcement_url}: HTTP {resp.status_code}")
                    return None

                soup = BeautifulSoup(resp.text, "html.parser")
                
                # 提取标题
                title_tag = soup.find(["h1", "h2"])
                title = title_tag.text.strip() if title_tag else "未知公告标题"

                # 提取正文容器
                content_div = soup.find("div", class_=lambda x: x and any(k in str(x) for k in ["content", "article", "detail", "ws-content"]))
                if not content_div:
                    # 容错：查找最大的 div
                    for div in soup.find_all("div"):
                        if len(div.text.strip()) > 300:
                            content_div = div
                            break

                content_html = str(content_div) if content_div else ""
                content_text = content_div.text.strip() if content_div else ""

                # 提取附件列表
                attachments: List[RawAttachmentItem] = []
                if content_div:
                    for a in content_div.find_all("a", href=True):
                        href = a["href"].strip()
                        att_name = a.text.strip() or "附件下载"
                        lower_href = href.lower()
                        for ext in [".xlsx", ".xls", ".docx", ".doc", ".pdf", ".zip", ".rar"]:
                            if ext in lower_href:
                                full_download_url = urljoin(self.base_url, href)
                                attachments.append(RawAttachmentItem(
                                    file_name=att_name,
                                    download_url=full_download_url,
                                    file_type=ext.lstrip(".")
                                ))
                                break

                # 尝试从正文或页面提取发布时间
                date_match = re.search(r"(\d{4})[年\-](\d{1,2})[月\-](\d{1,2})", content_text[:300])
                if date_match:
                    pub_date = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
                else:
                    pub_date = datetime.now().strftime("%Y-%m-%d")

                return RawAnnouncementDetail(
                    source_id=self.source_id,
                    url=announcement_url,
                    title=title,
                    content_html=content_html,
                    content_text=content_text,
                    publish_date=pub_date,
                    attachments=attachments,
                    crawl_time=datetime.now()
                )
            except Exception as e:
                logger.error(f"[{self.source_id}] 解析详情页异常 {announcement_url}: {e}")
                return None
