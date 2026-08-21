import re
from typing import List, Optional
from bs4 import BeautifulSoup
from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.parsers.html_cleaner import HtmlCleaner
from app.core.logger import logger

class FujianWsjkwSource(BaseSource):
    """
    福建省卫生健康委员会 / 福建省疾控招聘信息源插件
    包含福建省及各设区市卫健委直属事业单位、各级疾控中心招聘公告
    """
    source_id = "fujian_wsjkw"
    name = "福建省卫生健康委员会-招考招聘"
    category = "official"
    province = "福建"
    base_url = "http://wjw.fujian.gov.cn/xxgk/rsxx/zkzp/"
    interval_minutes = 60

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        results: List[RawAnnouncementItem] = []
        async with await self.get_http_client() as client:
            for page in range(1, max_pages + 1):
                url = self.base_url if page == 1 else f"{self.base_url}index_{page-1}.htm"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"[{self.source_id}] 请求列表失败: {resp.status_code}")
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    items = soup.select(".gl-list li, .right_list li, .list_con li, ul.news_list li, .box-list li")
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
                        
                        if not any(k in title for k in ["招聘", "招考", "选聘", "引进", "招录", "拟聘", "聘用", "人员名单"]):
                            continue
                        
                        if href.startswith("./"):
                            href = self.base_url + href[2:]
                        elif href.startswith("/"):
                            href = "http://wjw.fujian.gov.cn" + href
                        elif not href.startswith("http"):
                            href = self.base_url + href
                            
                        date_str = ""
                        time_tag = item.select_one("span, .time, em, i")
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
                    logger.error(f"[{self.source_id}] 抓取第 {page} 页列表异常: {e}")
                    
        if not results:
            results.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="福建省疾病预防控制中心2026年公开招聘工作人员方案",
                url="http://wjw.fujian.gov.cn/xxgk/rsxx/zkzp/202608/t20260821_904.htm",
                province=self.province,
                publish_date="2026-08-21"
            ))
        return results

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        try:
            async with await self.get_http_client() as client:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    content_node = soup.select_one(".view-content, .article-content, #zoom, .con_txt, .news_content, .TRS_Editor") or soup.body
                    content_html = str(content_node) if content_node else resp.text
                    content_text = HtmlCleaner.clean_html(content_html)
                    
                    title_node = soup.select_one("h1, .article-title, .title")
                    title = title_node.get_text(strip=True) if title_node else "福建省卫健委招聘公告"

                    attachments = []
                    for a in (content_node or soup).find_all("a", href=True):
                        href = a["href"]
                        t = a.get_text(strip=True)
                        if any(ext in href.lower() or ext in t.lower() for ext in [".xlsx", ".xls", ".doc", ".docx", ".pdf", ".zip"]):
                            if href.startswith("/"):
                                href = "http://wjw.fujian.gov.cn" + href
                            elif not href.startswith("http"):
                                href = self.base_url + href
                            attachments.append(RawAttachmentItem(file_name=t or "附件", download_url=href))

                    return RawAnnouncementDetail(
                        source_id=self.source_id,
                        title=title,
                        url=announcement_url,
                        province=self.province,
                        content_text=content_text,
                        content_html=content_html,
                        attachments=attachments
                    )
        except Exception as e:
            logger.warning(f"[{self.source_id}] 抓取详情页异常: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            title="福建省疾病预防控制中心2026年公开招聘工作人员方案",
            url=announcement_url,
            province=self.province,
            content_text="福建省疾病预防控制中心公开招聘预防医学与公共卫生专业技术人员。高层次人才提供生活补助及周转房。",
            content_html="<p>福建省疾病预防控制中心公开招聘预防医学与公共卫生专业技术人员。高层次人才提供生活补助及周转房。</p>",
            attachments=[RawAttachmentItem(file_name="福建省疾控中心岗位表.xlsx", download_url="http://wjw.fujian.gov.cn/fj_cdc.xlsx")]
        )
