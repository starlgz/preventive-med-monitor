import re
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

SHIYEBIAN_PROVINCES: List[Tuple[str, str]] = [
    ("beijing", "北京"), ("shanghai", "上海"), ("tianjin", "天津"), ("chongqing", "重庆"),
    ("hebei", "河北"), ("shanxi", "山西"), ("liaoning", "辽宁"), ("jilin", "吉林"),
    ("heilongjiang", "黑龙江"), ("jiangsu", "江苏"), ("zhejiang", "浙江"), ("anhui", "安徽"),
    ("fujian", "福建"), ("jiangxi", "江西"), ("shandong", "山东"), ("henan", "河南"),
    ("hubei", "湖北"), ("hunan", "湖南"), ("guangdong", "广东"), ("hainan", "海南"),
    ("sichuan", "四川"), ("guizhou", "贵州"), ("yunnan", "云南"), ("shaanxi", "陕西"),
    ("gansu", "甘肃"), ("qinghai", "青海"), ("taiwan", "台湾"), ("neimenggu", "内蒙古"),
    ("guangxi", "广西"), ("xizang", "西藏"), ("ningxia", "宁夏"), ("xinjiang", "新疆")
]

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

        async with await self.get_http_client(timeout=5.0) as client:
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
        async with await self.get_http_client(timeout=5.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code != 200:
                    logger.warning(f"[{self.source_id}] 抓取详情页失败 {announcement_url}: HTTP {resp.status_code}")
                    return None

                soup = BeautifulSoup(resp.text, "html.parser")
                
                # 提取标题
                title_tag = soup.find(["h1", "h2"])
                title = title_tag.text.strip() if title_tag else "未知公告标题"

                # 提取省份与城市归属（从面包屑导航 ws-position 提取）
                province = "全国"
                city = "全国"
                pos_div = soup.find("div", class_=lambda x: x and ("position" in str(x) or "crumb" in str(x) or "ws-position" in str(x)))
                if pos_div:
                    pos_text = pos_div.text.strip()
                    parts = [re.sub(r"事业单位招聘|招聘|考试|网|首页", "", p).strip() for p in re.split(r"[>›/»]", pos_text) if p.strip()]
                    parts = [p for p in parts if p]
                    if len(parts) >= 1 and parts[0]:
                        province = parts[0]
                    if len(parts) >= 2 and parts[1]:
                        city = parts[1]

                # 提取发布时间（优先从 ws-info 结构化元数据提取）
                pub_date = None
                info_div = soup.find("div", class_=lambda x: x and ("ws-info" in str(x) or "info" in str(x) or "meta" in str(x)))
                if info_div:
                    d_match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", info_div.text)
                    if d_match:
                        pub_date = f"{d_match.group(1)}-{int(d_match.group(2)):02d}-{int(d_match.group(3)):02d}"

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

                if not pub_date:
                    # 从正文兜底提取发布时间
                    date_match = re.search(r"(\d{4})[年\-](\d{1,2})[月\-](\d{1,2})", content_text[:300])
                    if date_match:
                        pub_date = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
                    else:
                        pub_date = datetime.now().strftime("%Y-%m-%d")

                # 提取附件列表（支持直接后缀与 download.php 转发链接）
                attachments: List[RawAttachmentItem] = []
                seen_down_urls = set()
                search_container = content_div or soup
                for a in search_container.find_all("a", href=True):
                    href = a["href"].strip()
                    att_name = a.text.strip()
                    lower_href = href.lower()
                    lower_name = att_name.lower()

                    is_att = False
                    file_type = "file"
                    for ext in [".xlsx", ".xls", ".docx", ".doc", ".pdf", ".zip", ".rar", ".7z", ".csv"]:
                        if ext in lower_href or ext in lower_name:
                            is_att = True
                            file_type = ext.lstrip(".")
                            break

                    if not is_att and ("/e/down/" in lower_href or "download.php" in lower_href):
                        is_att = True
                        file_type = "file"

                    if is_att:
                        full_download_url = urljoin(self.base_url, href)
                        # 过滤掉宣传/APP下载类杂质
                        if full_download_url not in seen_down_urls and not any(skip in lower_name for skip in ["app", "客户端", "刷题", "真题库", "微信小程序"]):
                            seen_down_urls.add(full_download_url)
                            attachments.append(RawAttachmentItem(
                                file_name=att_name or "附件下载",
                                download_url=full_download_url,
                                file_type=file_type
                            ))

                return RawAnnouncementDetail(
                    source_id=self.source_id,
                    url=announcement_url,
                    title=title,
                    content_html=content_html,
                    content_text=content_text,
                    publish_date=pub_date,
                    province=province,
                    city=city,
                    attachments=attachments,
                    crawl_time=datetime.now()
                )
            except Exception as e:
                logger.error(f"[{self.source_id}] 解析详情页异常 {announcement_url}: {e}")
                return None


class ShiyebianProvinceSource(BaseSource):
    """
    全国事业单位招聘网 (shiyebian.com) - 针对指定省份频道的采集源
    """
    category: str = "aggregator"
    enabled: bool = True
    interval_minutes: int = 30

    def __init__(self, province_code: str, province_name: str):
        super().__init__()
        self.province_code = province_code
        self.province = province_name
        self.source_id = f"shiyebian_{province_code}"
        self.name = f"事业单位招聘网-{province_name}"
        self.base_url = f"https://www.shiyebian.com/{province_code}/"

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取省份频道的最新招聘公告"""
        items: List[RawAnnouncementItem] = []
        seen_urls = set()

        async with await self.get_http_client(timeout=5.0) as client:
            try:
                resp = await client.get(self.base_url)
                if resp.status_code != 200:
                    return items

                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    title = a.text.strip()
                    if "/xinxi/" in href and re.search(r"/xinxi/\d+\.html", href):
                        full_url = urljoin("https://www.shiyebian.com", href)
                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)
                        items.append(RawAnnouncementItem(
                            source_id=self.source_id,
                            title=title,
                            url=full_url,
                            publish_date=datetime.now().strftime("%Y-%m-%d"),
                            province=self.province,
                            city=self.province
                        ))
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取省份频道异常 {self.base_url}: {e}")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """复用 ShiyebianSource 详情页解析逻辑并注入省份默认值"""
        shiyebian_base = ShiyebianSource()
        detail = await shiyebian_base.fetch_detail(announcement_url)
        if detail:
            detail.source_id = self.source_id
            if not detail.province or detail.province == "全国":
                detail.province = self.province
            if not detail.city or detail.city == "全国":
                detail.city = self.province
        return detail
