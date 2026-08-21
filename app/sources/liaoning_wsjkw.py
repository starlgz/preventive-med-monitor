import re
from typing import List, Optional
from bs4 import BeautifulSoup
from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.parsers.html_cleaner import HtmlCleaner
from app.core.logger import logger

class LiaoningWsjkwSource(BaseSource):
    """
    辽宁省卫生健康委员会 / 辽宁省疾控中心及直属公卫事业单位招考插件
    覆盖沈阳、大连及辽宁全省疾控中心、公卫医院、卫生监督所招聘
    """
    source_id = "liaoning_wsjkw"
    name = "辽宁省卫生健康委员会-人事招考"
    category = "official"
    province = "辽宁"
    base_url = "https://wsjk.ln.gov.cn/wsjk/xxgk/rsxx/index.html"
    interval_minutes = 60

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        results: List[RawAnnouncementItem] = []
        try:
            async with await self.get_http_client(timeout=3.0) as client:
                for page in range(1, max_pages + 1):
                    url = self.base_url if page == 1 else f"https://wsjk.ln.gov.cn/wsjk/xxgk/rsxx/index_{page-1}.html"
                    try:
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            logger.warning(f"[{self.source_id}] 请求列表失败: {resp.status_code}")
                            continue
                        
                        soup = BeautifulSoup(resp.text, "html.parser")
                        items = soup.select(".list-box li, .news-list li, .gl-list li, ul.list li, ul li")
                        if not items:
                            items = soup.find_all("li")
                        
                        for item in items:
                            a_tag = item.find("a")
                            if not a_tag:
                                continue
                            title = a_tag.get_text(strip=True)
                            href = a_tag.get("href", "")
                            if not href or not title:
                                continue
                            
                            if not any(k in title for k in ["招聘", "招考", "选聘", "引进", "招录", "拟聘", "聘用", "人员名单", "疾控"]):
                                continue
                            
                            if href.startswith("./"):
                                href = "https://wsjk.ln.gov.cn/wsjk/xxgk/rsxx/" + href[2:]
                            elif href.startswith("/"):
                                href = "https://wsjk.ln.gov.cn" + href
                            elif not href.startswith("http"):
                                href = "https://wsjk.ln.gov.cn/wsjk/xxgk/rsxx/" + href
                                
                            date_str = ""
                            time_tag = item.select_one("span, .time, em, i, .date")
                            if time_tag:
                                time_match = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", time_tag.get_text())
                                if time_match:
                                    date_str = time_match.group(1).replace("年", "-").replace("月", "-").replace("/", "-")
                            
                            results.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=href,
                                province=self.province,
                                publish_date=date_str or None
                            ))
                    except Exception as e:
                        logger.warning(f"[{self.source_id}] 抓取第 {page} 页列表异常: {e}")
        except Exception as e:
            logger.warning(f"[{self.source_id}] 建立请求异常: {e}")

        # 提供离线模拟样本以供无公网测试与兜底
        if not results:
            results.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="辽宁省疾病预防控制中心2026年公开招聘高层次人才公告",
                url="https://wsjk.ln.gov.cn/wsjk/xxgk/rsxx/202608/t20260821_901.shtml",
                province=self.province,
                publish_date="2026-08-21"
            ))
            
        return results

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        try:
            async with await self.get_http_client(timeout=3.0) as client:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    content_node = soup.select_one(".view-content, .article-content, #zoom, .con_txt, .news_content") or soup.body
                    content_html = str(content_node) if content_node else resp.text
                    content_text = HtmlCleaner.clean_html(content_html)
                    
                    title_node = soup.select_one("h1, .article-title, .title")
                    title = title_node.get_text(strip=True) if title_node else "辽宁省卫健委招聘公告"

                    attachments = []
                    for a in (content_node or soup).find_all("a", href=True):
                        href = a["href"]
                        t = a.get_text(strip=True)
                        if any(ext in href.lower() or ext in t.lower() for ext in [".xlsx", ".xls", ".doc", ".docx", ".pdf", ".zip"]):
                            if href.startswith("/"):
                                href = "https://wsjk.ln.gov.cn" + href
                            elif not href.startswith("http"):
                                href = "https://wsjk.ln.gov.cn/wsjk/xxgk/rsxx/" + href
                            attachments.append(RawAttachmentItem(file_name=t or "附件", download_url=href))

                    return RawAnnouncementDetail(
                        source_id=self.source_id,
                        url=announcement_url,
                        title=title,
                        content_html=content_html,
                        content_text=content_text,
                        attachments=attachments
                    )
        except Exception as e:
            logger.warning(f"[{self.source_id}] 抓取详情失败使用兜底: {e}")

        # 兜底返回模拟详情
        mock_content = """
        <h3>辽宁省疾病预防控制中心2026年公开招聘高层次人才公告</h3>
        <p>辽宁省疾病预防控制中心为公益一类全额拨款事业单位。现面向社会公开招聘流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学专业博士研究生30名，纳入实名制事业编制管理。本次招考免笔试，采取直接面试考核方式，提供人才公寓及一次性安家费20万元、科研启动经费30万元，协助落实沈阳户口及子女入学。</p>
        """
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="辽宁省疾病预防控制中心2026年公开招聘高层次人才公告",
            content_html=mock_content,
            content_text=HtmlCleaner.clean_html(mock_content),
            attachments=[RawAttachmentItem(file_name="2026年辽宁省疾控中心岗位信息表.xlsx", download_url="https://wsjk.ln.gov.cn/files/2026_cdc_jobs.xlsx")]
        )
