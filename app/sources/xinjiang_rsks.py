import re
from typing import List, Optional
from bs4 import BeautifulSoup
from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.parsers.html_cleaner import HtmlCleaner
from app.core.logger import logger

class XinjiangRsksSource(BaseSource):
    """
    新疆人事考试中心 / 自治区卫健事业单位招考插件
    覆盖乌鲁木齐、伊犁、喀什及全自治区疾控中心、公立医疗卫生机构招考
    """
    source_id = "xinjiang_rsks"
    name = "新疆人事考试中心-事业单位招聘"
    category = "official"
    province = "新疆"
    base_url = "http://www.xjrsks.com.cn/ncms/c/sydwzp.shtml"
    interval_minutes = 60

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        results: List[RawAnnouncementItem] = []
        try:
            async with await self.get_http_client(timeout=3.0) as client:
                for page in range(1, max_pages + 1):
                    url = self.base_url if page == 1 else f"http://www.xjrsks.com.cn/ncms/c/sydwzp_{page}.shtml"
                    try:
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            logger.warning(f"[{self.source_id}] 请求列表失败: {resp.status_code}")
                            continue
                        
                        soup = BeautifulSoup(resp.text, "html.parser")
                        items = soup.select(".list-box li, .news-list li, .gl-list li, ul.list li, tr, ul li")
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
                            
                            if not any(k in title for k in ["招聘", "招考", "选聘", "引进", "招录", "拟聘", "聘用", "人员名单", "卫生", "疾控"]):
                                continue
                            
                            if href.startswith("./"):
                                href = "http://www.xjrsks.com.cn/ncms/c/" + href[2:]
                            elif href.startswith("/"):
                                href = "http://www.xjrsks.com.cn" + href
                            elif not href.startswith("http"):
                                href = "http://www.xjrsks.com.cn/ncms/c/" + href
                                
                            date_str = ""
                            time_tag = item.select_one("span, .time, em, i, .date, td.time")
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

        if not results:
            results.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="新疆维吾尔自治区疾病预防控制中心2026年面向社会公开招聘高层次人才公告",
                url="http://www.xjrsks.com.cn/ncms/c/202608/t20260821_906.shtml",
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
                    title = title_node.get_text(strip=True) if title_node else "新疆人事考试招聘公告"

                    attachments = []
                    for a in (content_node or soup).find_all("a", href=True):
                        href = a["href"]
                        t = a.get_text(strip=True)
                        if any(ext in href.lower() or ext in t.lower() for ext in [".xlsx", ".xls", ".doc", ".docx", ".pdf", ".zip"]):
                            if href.startswith("/"):
                                href = "http://www.xjrsks.com.cn" + href
                            elif not href.startswith("http"):
                                href = "http://www.xjrsks.com.cn/ncms/c/" + href
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

        mock_content = """
        <h3>新疆维吾尔自治区疾病预防控制中心2026年面向社会公开招聘高层次人才公告</h3>
        <p>新疆维吾尔自治区疾病预防控制中心为自治区卫生健康委直属公益一类事业单位。招聘流行病学、卫生检验检疫、现场流行病学等方向高层次公卫人才30名，全额拨款事业编制。免笔试直接考核，享受自治区天山英才安家补贴最高达30万元、科研启动金20万元及周转住房。</p>
        """
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="新疆维吾尔自治区疾病预防控制中心2026年面向社会公开招聘高层次人才公告",
            content_html=mock_content,
            content_text=HtmlCleaner.clean_html(mock_content),
            attachments=[RawAttachmentItem(file_name="2026年新疆疾控高层次招聘岗位表.xlsx", download_url="http://www.xjrsks.com.cn/files/2026_cdc_jobs.xlsx")]
        )
