import asyncio
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import AsyncSessionLocal, engine, Base
from app.sources.registry import SourceRegistry
from app.sources.shandong_wsjkw import ShandongWsjkwSource
from app.sources.hubei_wsjkw import HubeiWsjkwSource
from app.rules.major_matcher import MajorMatcher
from app.notifications.service import notification_service
from app.web.dashboard import get_analytics_distribution, export_jobs_data
from app.sources.base import RawAnnouncementItem

class TestPhase12Improvements(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session = AsyncSessionLocal()

    async def asyncTearDown(self):
        await self.session.close()

    def test_sources_discovery(self):
        """测试省份爬虫源注册与发现"""
        sources = SourceRegistry.discover_and_register()
        self.assertIn("shandong_wsjkw", sources)
        self.assertIn("hubei_wsjkw", sources)
        self.assertIn("guangdong_rsks", sources)
        self.assertIn("zhejiang_rsks", sources)
        self.assertGreater(len(sources), 5)

    async def test_sources_mock_fetch(self):
        """测试山东与湖北卫健爬虫解析器逻辑（mock 网络）"""
        mock_sd = [RawAnnouncementItem(source_id="shandong_wsjkw", title="山东卫健委测试招聘", url="http://test.sd", province="山东")]
        mock_hb = [RawAnnouncementItem(source_id="hubei_wsjkw", title="湖北卫健委测试招聘", url="http://test.hb", province="湖北")]

        sd_source = ShandongWsjkwSource()
        hb_source = HubeiWsjkwSource()

        with patch.object(sd_source, 'fetch_announcements', new=AsyncMock(return_value=mock_sd)):
            sd_announcements = await sd_source.fetch_latest_announcements()
            self.assertGreater(len(sd_announcements), 0)
            self.assertEqual(sd_announcements[0].province, "山东")

        with patch.object(hb_source, 'fetch_announcements', new=AsyncMock(return_value=mock_hb)):
            hb_announcements = await hb_source.fetch_latest_announcements()
            self.assertGreater(len(hb_announcements), 0)
            self.assertEqual(hb_announcements[0].province, "湖北")

    def test_expanded_major_matcher(self):
        """测试专业扩充词典精准识别"""
        engine_match = MajorMatcher()

        m1 = engine_match.match_major("劳动卫生与环境卫生学", "市疾控中心职业病科")
        self.assertIn(m1["match_level"], [4, 5])
        self.assertIsInstance(m1.get("matched_keywords", []), list)

        m2 = engine_match.match_major("营养与食品卫生学", "省疾控食品安全监测所")
        self.assertIn(m2["match_level"], [4, 5])

        m3 = engine_match.match_major("卫生毒理学", "理化检验与毒理室")
        self.assertIn(m3["match_level"], [3, 4, 5])

        m4 = engine_match.match_major("公共卫生硕士(MPH)", "社区卫生服务中心")
        self.assertIn(m4["match_level"], [4, 5])

        m5 = engine_match.match_major("基础医学/病原生物学", "检验科")
        self.assertIn(m5["match_level"], [1, 2, 3, 4, 5])

        m6 = engine_match.match_major("预防医学", "疾控中心慢病科")
        self.assertEqual(m6["match_level"], 5)

    async def test_web_analytics_and_export(self):
        """测试多维图表数据聚合接口与导出功能"""
        analytics = await get_analytics_distribution(session=self.session)
        self.assertIn("province_distribution", analytics)
        self.assertIn("star_distribution", analytics)

        result = await export_jobs_data(session=self.session, format="xlsx")
        self.assertIsNotNone(result)

    def test_notification_service_init(self):
        """测试通知服务初始化"""
        self.assertIsNotNone(notification_service)

if __name__ == "__main__":
    unittest.main()
