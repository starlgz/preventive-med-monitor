import asyncio
from app.dedup.simhash import SimHashDedup
from app.dedup.dual_engine import DualDeduplicationEngine
from app.ai.evaluator import AIEligibilityEvaluator
from app.sources.provinces_pool import PROVINCE_SOURCES

async def main():
    print("=== 1. 测试 SimHash 文本指纹与公告变更追踪 (SimHashDedup) ===")
    text_orig = "2026年浙江省疾病预防控制中心公开招聘事业编制人员公告，报名截止时间2026年8月25日。"
    text_ext = "2026年浙江省疾病预防控制中心公开招聘事业编制人员补充通知，原定报名时间延长至2026年8月30日。"
    text_diff = "2026年广东省广州市白云区卫生健康系统公开招聘事业单位工作人员公告。"

    sim_ext = SimHashDedup.similarity(text_orig, text_ext)
    sim_diff = SimHashDedup.similarity(text_orig, text_diff)
    print(f"原公告与延期公告相似度: {sim_ext:.2f} (高相似度，判定为延期/补充变更)")
    print(f"原公告与不同省份公告相似度: {sim_diff:.2f} (低相似度，判定为独立新公告)")
    assert sim_ext > 0.7
    assert sim_diff < 0.7

    change_res = SimHashDedup.detect_announcement_change(
        old_title="2026年浙江省疾病预防控制中心招聘公告",
        old_text=text_orig,
        new_title="2026年浙江省疾病预防控制中心招聘补充公告",
        new_text=text_ext
    )
    print(f"变更检测结果: is_update={change_res['is_update']}, reason={change_res['reason']}")
    assert change_res['is_update'] is True
    print("SimHash 与变更追踪算法全部通过！(PASS)")

    print("\n=== 2. 测试 AI 报考资格与风险研判模块 (AIEligibilityEvaluator) ===")
    sample_job = {
        "unit_name": "杭州市疾控中心",
        "unit_type": "疾控中心",
        "job_name": "流行病学与应急调查岗",
        "education": "硕士研究生",
        "major_raw": "预防医学、流行病与卫生统计学",
        "cert_requirements": "公共卫生执业医师",
        "announcement_title": "2026年公开招聘事业编制人员公告",
        "match_level": 5,
        "is_bianzhi": 1
    }
    user_profile = {
        "major": "预防医学",
        "education": "硕士研究生",
        "is_fresh_grad": True,
        "has_cert": True,
        "age": 26
    }
    ai_res = await AIEligibilityEvaluator.evaluate_eligibility(sample_job, user_profile)
    print(f"AI 研判输出 ({ai_res.get('engine')}):")
    print(f"  - 资格判定: {ai_res.get('eligibility')}")
    print(f"  - 匹配评分: {ai_res.get('match_score')}")
    print(f"  - 编制安全: {ai_res.get('is_bianzhi_safe')}")
    print(f"  - 研判理由: {ai_res.get('reason')}")
    print(f"  - 风险提示: {ai_res.get('risk_warnings')}")
    assert ai_res.get("eligibility") is True
    print("AI 报考资格与风险研判全部通过！(PASS)")

    print("\n=== 3. 测试全国 31 省市核心采集源池配置 (PROVINCE_SOURCES) ===")
    print(f"已收录并纳管的全国省级/区域招考源总数: {len(PROVINCE_SOURCES)} 个")
    for src in PROVINCE_SOURCES[:6]:
        print(f"  - [{src['province']}] {src['name']} (URL: {src['url']})")
    assert len(PROVINCE_SOURCES) >= 10
    print("全国省市核心源池配置全部通过！(PASS)")

    print("\n🎉 进阶核心功能全项测试 100% PASS！")

if __name__ == "__main__":
    asyncio.run(main())
