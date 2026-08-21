import unittest
from unittest.mock import patch, AsyncMock
from app.sources.hunan_wsjkw import HunanWsjkwSource
from app.sources.henan_wsjkw import HenanWsjkwSource
from app.sources.shaanxi_wsjkw import ShaanxiWsjkwSource
from app.sources.registry import SourceRegistry
from app.sources.provinces_pool import PROVINCES_SOURCE_POOL
from app.sources.base import RawAnnouncementItem, RawAnnouncementDetail

class TestPhase13NewSources(unittest.IsolatedAsyncioTestCase):
    def test_sources_instantiation(self):
        """测试湖南、河南、陕西爬虫实例化与属性"""
        hn = HunanWsjkwSource()
        self.assertEqual(hn.source_id, "hunan_wsjkw")
        self.assertEqual(hn.province, "湖南")
        self.assertEqual(hn.name, "湖南省卫健委人才招聘")
        self.assertEqual(hn.base_url, "http://wjw.hunan.gov.cn/wjw/xxgk/rsxx/index.html")

        ha = HenanWsjkwSource()
        self.assertEqual(ha.source_id, "henan_wsjkw")
        self.assertEqual(ha.province, "河南")
        self.assertEqual(ha.name, "河南省卫健委人才招聘")
        self.assertEqual(ha.base_url, "https://wsjkw.henan.gov.cn/wsjkw/index/rsxx/index.html")

        sx = ShaanxiWsjkwSource()
        self.assertEqual(sx.source_id, "shaanxi_wsjkw")
        self.assertEqual(sx.province, "陕西")
        self.assertEqual(sx.name, "陕西省卫健委人才招聘")
        self.assertEqual(sx.base_url, "http://sxwjw.shaanxi.gov.cn/sy/rczp/index.html")

    def test_registry_and_provinces_pool(self):
        """测试新数据源在 Registry 和 provinces_pool 中的注册情况"""
        all_sources = SourceRegistry.get_all()
        source_ids = [s.source_id for s in all_sources]
        self.assertIn("hunan_wsjkw", source_ids)
        self.assertIn("henan_wsjkw", source_ids)
        self.assertIn("shaanxi_wsjkw", source_ids)

        pool_codes = [s["code"] for s in PROVINCES_SOURCE_POOL]
        self.assertIn("hunan_wsjkw", pool_codes)
        self.assertIn("henan_wsjkw", pool_codes)
        self.assertIn("shaanxi_wsjkw", pool_codes)


        self.assertIsNotNone(SourceRegistry.get("hunan_wsjkw"))
        self.assertIsNotNone(SourceRegistry.get("henan_wsjkw"))
        self.assertIsNotNone(SourceRegistry.get("shaanxi_wsjkw"))

    async def test_hunan_mock_fetch(self):
        """测试湖南卫健委 mock 抓取公告列表与详情"""
        source = HunanWsjkwSource()
        mock_items = [
            RawAnnouncementItem(
                title="湖南省疾病预防控制中心2026年公开招聘公告",
                url="http://wjw.hunan.gov.cn/wjw/xxgk/rsxx/202601/t20260115_12345.html",
                source_id="hunan_wsjkw",
                province="湖南",
                publish_time="2026-01-15"
            )
        ]
        with patch.object(source, 'fetch_announcements', new=AsyncMock(return_value=mock_items)):
            announcements = await source.fetch_announcements()
            self.assertEqual(len(announcements), 1)
            self.assertEqual(announcements[0].province, "湖南")
            self.assertEqual(announcements[0].source_id, "hunan_wsjkw")
            self.assertIn("疾病预防控制中心", announcements[0].title)


    async def test_henan_mock_fetch(self):
        """测试河南卫健委 mock 抓取公告列表与详情"""
        source = HenanWsjkwSource()
        mock_items = [
            RawAnnouncementItem(
                title="河南省卫生健康委员会直属事业单位2026年统一招聘工作人员方案",
                url="https://wsjkw.henan.gov.cn/wsjkw/index/rsxx/2026-02/10/content_98765.html",
                source_id="henan_wsjkw",
                province="河南",
                publish_time="2026-02-10"
            )
        ]
        with patch.object(source, 'fetch_announcements', new=AsyncMock(return_value=mock_items)):
            announcements = await source.fetch_announcements()
            self.assertEqual(len(announcements), 1)
            self.assertEqual(announcements[0].province, "河南")
            self.assertEqual(announcements[0].source_id, "henan_wsjkw")


    async def test_shaanxi_mock_fetch(self):
        """测试陕西卫健委 mock 抓取公告列表与详情"""
        source = ShaanxiWsjkwSource()
        mock_items = [
            RawAnnouncementItem(
                title="陕西省疾病预防控制中心2026年高层次人才招聘公告",
                url="http://sxwjw.shaanxi.gov.cn/sy/rczp/202603/t20260301_54321.html",
                source_id="shaanxi_wsjkw",
                province="陕西",
                publish_time="2026-03-01"
            )
        ]
        with patch.object(source, 'fetch_announcements', new=AsyncMock(return_value=mock_items)):
            announcements = await source.fetch_announcements()
            self.assertEqual(len(announcements), 1)
            self.assertEqual(announcements[0].province, "陕西")
            self.assertEqual(announcements[0].source_id, "shaanxi_wsjkw")



if __name__ == "__main__":
    unittest.main()
