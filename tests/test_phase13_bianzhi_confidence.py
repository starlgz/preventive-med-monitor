import unittest
from app.rules.bianzhi_evaluator import BianzhiEvaluator

class TestPhase13BianzhiConfidence(unittest.TestCase):
    """
    第二轮迭代任务2测试：编制研判 confidence, evidence_chain, bianzhi_type
    """

    def test_bianzhi_confidence_full_quane(self):
        """测试全额事业编制研判及置信度/证据链"""
        res = BianzhiEvaluator.evaluate(
            job_name="公共卫生医师",
            unit_name="湖南省疾病预防控制中心",
            unit_type="疾控中心",
            other_requirements="全额拨款事业单位，办理正式编制入编手续",
            announcement_title="2026年湖南省疾控中心公开招聘事业编制人员公告",
            announcement_text="本次招聘属于事业单位公开招聘工作人员，纳入机构编制实名制管理。"
        )
        self.assertEqual(res["is_bianzhi"], 1)
        self.assertEqual(res["bianzhi_type"], "全额事业编")
        self.assertGreaterEqual(res["confidence"], 0.85)
        self.assertIn("confidence", res)
        self.assertIn("evidence_chain", res)
        self.assertTrue(len(res["evidence_chain"]) >= 2)
        self.assertTrue(any("事业" in ev or "入编" in ev or "实名制" in ev for ev in res["evidence_chain"]))

    def test_bianzhi_confidence_chane(self):
        """测试差额事业编研判及置信度/证据链"""
        res = BianzhiEvaluator.evaluate(
            job_name="慢病流调员",
            unit_name="某市第二人民医院",
            unit_type="综合医院/专科医院",
            other_requirements="差额拨款事业单位，差额补助事业编制",
            announcement_title="2026年公开招聘差额事业编制工作人员公告",
            announcement_text="本单位为差额拨款事业单位，招聘人员纳入差额补助编制管理。"
        )
        self.assertEqual(res["is_bianzhi"], 1)
        self.assertEqual(res["bianzhi_type"], "差额事业编")
        self.assertGreaterEqual(res["confidence"], 0.70)
        self.assertIn("差额拨款事业单位", res["evidence_chain"])

    def test_bianzhi_confidence_beianzhi(self):
        """测试报备员额/备案制/存疑黄标研判"""
        res = BianzhiEvaluator.evaluate(
            job_name="公卫医师",
            unit_name="某省人民医院",
            unit_type="综合医院/专科医院",
            other_requirements="实行公立医院人员总量控制，按报备员额管理",
            announcement_title="2026年人员总量招聘公告",
            announcement_text="本次招聘实行报备员额制管理，享受同工同酬待遇。"
        )
        self.assertEqual(res["is_bianzhi"], 2)
        self.assertEqual(res["bianzhi_type"], "报备员额")
        self.assertGreaterEqual(res["confidence"], 0.60)
        self.assertTrue(any("报备员额" in ev or "人员总量" in ev or "同工同酬" in ev for ev in res["evidence_chain"]))

    def test_bianzhi_confidence_contract(self):
        """测试合同制/劳务派遣红标研判"""
        res = BianzhiEvaluator.evaluate(
            job_name="采样辅助人员",
            unit_name="某区卫生监督所",
            unit_type="卫生监督",
            other_requirements="劳务派遣用工，与第三方签订劳动合同，不占编制，合同制聘用",
            announcement_title="2026年招聘编外劳务派遣人员公告",
            announcement_text="本次招聘人员为编外聘用，实行合同制劳务派遣，不纳入事业单位编制。"
        )
        self.assertEqual(res["is_bianzhi"], 0)
        self.assertEqual(res["bianzhi_type"], "合同制")
        self.assertGreaterEqual(res["confidence"], 0.90)  # 置信度高表明确定是非编
        self.assertTrue(any("劳务派遣" in ev or "合同制" in ev or "第三方" in ev for ev in res["evidence_chain"]))

    def test_bianzhi_confidence_unknown(self):
        """测试信息不足时的未知判定"""
        res = BianzhiEvaluator.evaluate(
            job_name="综合管理岗",
            unit_name="某健康服务机构",
            unit_type="其他事业单位",
            other_requirements="本科及以上学历",
            announcement_title="2026年招聘工作人员公告",
            announcement_text="招聘工作人员数名。"
        )
        self.assertEqual(res["is_bianzhi"], 2)
        self.assertEqual(res["bianzhi_type"], "未知")
        self.assertLessEqual(res["confidence"], 0.50)
        self.assertIsInstance(res["evidence_chain"], list)

if __name__ == "__main__":
    unittest.main()
