from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor
from app.sources.guangdong_rsks import GuangdongRsksSource
from app.sources.zhejiang_wsjkw import ZhejiangWsjkwSource
from app.sources.jiangsu_wsjkw import JiangsuWsjkwSource
from app.sources.sichuan_rsks import SichuanRsksSource
from app.sources.shanghai_rsks import ShanghaiRsksSource
from app.sources.beijing_rsks import BeijingRsksSource
from app.sources.hubei_wsjkw import HubeiWsjkwSource

@pytest.mark.asyncio
async def test_provincial_spiders_fetch():
    mock_html = """
    <html>
      <body>
        <div class="list">
          <a href="/content_123.html">2024年某省疾病预防控制中心公开招聘预防医学编制人员公告 2024-05-10</a>
          <a href="/content_456.html">某市卫生健康委员会直属事业单位招聘公卫医师</a>
        </div>
      </body>
    </html>
    """
    sources = [
        GuangdongRsksSource(),
        ZhejiangWsjkwSource(),
        JiangsuWsjkwSource(),
        SichuanRsksSource(),
        ShanghaiRsksSource(),
        BeijingRsksSource(),
        HubeiWsjkwSource()
    ]
    for sp in sources:
        assert sp.source_id is not None
        assert sp.name is not None
        assert sp.province in ["广东", "浙江", "江苏", "四川", "上海", "北京", "湖北"]
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = mock_html
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            items = await sp.fetch_announcements(max_pages=1)
            assert isinstance(items, list)
            assert len(items) >= 1
            assert "公告" in items[0].title or "招聘" in items[0].title

def test_bianzhi_evaluator_deep_rules():
    # 1. 劳务派遣 / 外包
    res_dispatch = BianzhiEvaluator.evaluate(
        job_name="消杀专员",
        unit_name="市疾控中心",
        announcement_text="本岗位采用劳务派遣用工形式，与人力资源公司签约。"
    )
    assert res_dispatch["is_bianzhi"] == 0
    assert res_dispatch["bianzhi_type"] in ["合同制", "劳务派遣"]
    assert res_dispatch["confidence"] >= 0.95
    assert any("劳务派遣" in ev for ev in res_dispatch["evidence_chain"])

    # 2. 合同制
    res_contract = BianzhiEvaluator.evaluate(
        job_name="公卫医师",
        unit_name="市一院",
        announcement_text="招聘编制外聘用工作人员，签订劳动合同，不占事业编制。"
    )
    assert res_contract["is_bianzhi"] == 0
    assert res_contract["bianzhi_type"] == "合同制"

    # 3. 报备员额 / 备案制
    res_beian = BianzhiEvaluator.evaluate(
        job_name="感控科医师",
        unit_name="省人民医院",
        announcement_text="实行公立医院人员总量备案制管理，享受同工同酬。"
    )
    assert res_beian["is_bianzhi"] == 2
    assert res_beian["bianzhi_type"] == "报备员额"

    # 4. 差额事业编
    res_chae = BianzhiEvaluator.evaluate(
        job_name="预防保健医师",
        unit_name="妇幼保健院",
        announcement_text="录用后享受差额拨款事业编制，办理正式落编手续。"
    )
    assert res_chae["is_bianzhi"] == 1
    assert res_chae["bianzhi_type"] == "差额事业编"

    # 5. 全额事业编
    res_quane = BianzhiEvaluator.evaluate(
        job_name="流行病调查岗",
        unit_name="省疾病预防控制中心",
        unit_type="疾控中心",
        announcement_text="纳入机构编制实名制管理，全额拨款事业编制。"
    )
    assert res_quane["is_bianzhi"] == 1
    assert res_quane["bianzhi_type"] == "全额事业编"
    assert res_quane["confidence"] >= 0.90

def test_talent_policy_extractor():
    text = "面向博士研究生及高级职称人才，免笔试直接面试，提供安家费50万元及科研启动金30万元，直聘事业编制高级公卫专员"
    policy = TalentPolicyExtractor.extract(announcement_text=text, job_name="疾控领军人才")
    assert policy["is_talent_introduction"] is True
    assert policy["is_exam_exempt"] is True
    assert policy["allowance_summary"] is not None
    assert "50万" in policy["allowance_summary"] or "30万" in policy["allowance_summary"]
    assert "博士" in policy["target_degree"] or "硕士" in policy["target_degree"]

@pytest.mark.asyncio
async def test_dashboard_recalculate_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/web/jobs/recalculate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert "recalculated_count" in data
