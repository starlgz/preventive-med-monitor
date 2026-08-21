"""全系统 11 个 Phase 最终总体验收与质量门禁套件"""

import asyncio
import sys
from loguru import logger
from app.core.database import AsyncSessionLocal
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.rules.priority_evaluator import PriorityEvaluator
from app.dedup.simhash import SimHashDedup
from app.dedup.dual_engine import DualDeduplicationEngine
from app.ai.evaluator import AIEligibilityEvaluator
from app.sources.provinces_pool import PROVINCE_SOURCES
from app.bot.dispatcher import BotCommandDispatcher
from app.core.pipeline import FullAutomationPipeline

async def run_final_audit():
    print("========================================================================")
    print("🏆 全国预防医学事业单位招聘实时监测系统 (V1.1) 最终验收与质量门禁自查")
    print("========================================================================")

    # 1. 专业匹配质量
    print("\n[Gate 1] 预防医学五星专业算法自查...")
    assert MajorMatcher.match("预防医学", "疾控中心", "公卫医师")["match_level"] == 5
    assert MajorMatcher.match("流行病与卫生统计学", "疾控中心", "流病岗")["match_level"] == 4
    assert MajorMatcher.match("公共卫生类", "疾控中心", "业务骨干")["match_level"] == 3
    assert MajorMatcher.match("计算机科学与技术", "卫健委", "网络管理")["match_level"] == 1
    print("  -> 五星专业匹配门禁 PASS")

    # 2. 编制判定质量
    print("\n[Gate 2] 岗位编制三色判定与证据链自查...")
    assert BianzhiEvaluator.evaluate("公卫岗", "疾控中心", "疾控中心", "实名制事业编制", "公开招聘事业编制公告")["is_bianzhi"] == 1
    assert BianzhiEvaluator.evaluate("临床医师", "市一医院", "综合医院/专科医院", "报备员额制", "公开招聘公告")["is_bianzhi"] == 2
    assert BianzhiEvaluator.evaluate("流调员", "疾控中心", "疾控中心", "劳务派遣合同工", "招聘编外派遣人员")["is_bianzhi"] == 0
    print("  -> 编制三色判定门禁 PASS")

    # 3. 优先级质量
    print("\n[Gate 3] 通知优先级与临期判定自查...")
    assert PriorityEvaluator.evaluate(5, 1, None)["priority_level"] == "A"
    assert PriorityEvaluator.evaluate(4, 1, None)["priority_level"] == "B"
    assert PriorityEvaluator.evaluate(5, 0, None)["priority_level"] == "D"
    print("  -> 通知优先级门禁 PASS")

    # 4. 双层去重与 SimHash 变更追踪
    print("\n[Gate 4] 双层去重与 SimHash 文本指纹自查...")
    t1 = "浙江省疾病预防控制中心2026年公开招聘事业编制人员公告，报名截止8月25日。"
    t2 = "【延期通知】浙江省疾病预防控制中心2026年公开招聘事业编制人员公告，报名截止延期至8月30日。"
    assert SimHashDedup.detect_announcement_change("浙江省疾控中心招聘公告", t1, "【延期通知】浙江省疾控中心招聘公告", t2)["is_update"] is True
    print("  -> SimHash 变更追踪门禁 PASS")

    # 5. AI 报考资格与风险研判
    print("\n[Gate 5] AI 报考研判与零成本规则漏斗自查...")
    ai_res = await AIEligibilityEvaluator.evaluate_eligibility(
        {"match_level": 5, "is_bianzhi": 1, "major_raw": "预防医学"},
        {"education_level": "本科", "is_fresh_grad": True}
    )
    assert ai_res["eligibility"] is True
    print("  -> AI 研判门禁 PASS")

    # 6. 全国 31 省市核心源池
    print("\n[Gate 6] 全国 31 省市核心源池覆盖自查...")
    assert len(PROVINCE_SOURCES) == 31
    print(f"  -> 已覆盖全国 {len(PROVINCE_SOURCES)} 个省级官方人社/卫健招考渠道 PASS")

    # 7. Telegram Bot 指令交互
    print("\n[Gate 7] Telegram Bot 指令中枢自查...")
    async with AsyncSessionLocal() as session:
        r_start = await BotCommandDispatcher.dispatch(session, "telegram:6213715919", "/start")
        assert "欢迎使用" in r_start
        r_today = await BotCommandDispatcher.dispatch(session, "telegram:6213715919", "/today")
        assert "今日" in r_today or "速报" in r_today
    print("  -> Bot 指令中枢门禁 PASS")

    # 8. 全链路端到端自动化管道
    print("\n[Gate 8] 全链路端到端自动化流水线自查...")
    async with AsyncSessionLocal() as session:
        pipe_res = await FullAutomationPipeline.run_pipeline(session, auto_push_notifications=True)
        assert pipe_res["status"] == "SUCCESS"
    print("  -> 全链路端到端流水线门禁 PASS")

    print("\n========================================================================")
    print("🎉 恭喜！全系统 11 个 Phase 与 8 项顶级门禁自查 100% 全部 PASS！具备投产上线标准！")
    print("========================================================================")

if __name__ == '__main__':
    asyncio.run(run_final_audit())
