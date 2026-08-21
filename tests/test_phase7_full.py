import asyncio
from datetime import datetime, timedelta
from app.rules.priority_evaluator import PriorityEvaluator
from app.rules.deduplicator import JobDeduplicator
from app.rules.priority_service import PriorityService
from app.core.database import AsyncSessionLocal
from app.models.entities import Job
from sqlalchemy import select

def test_priority_evaluator():
    print("=== 1. 优先级判定规则算法测试 (PriorityEvaluator) ===")
    now = datetime.now()
    
    cases = [
        # S 级测试: 5星 + 绿标 + 截止时间 <= 3天
        {
            "desc": "S 级 (5星 + 绿标在编 + 临期2天)",
            "ml": 5, "bz": 1, "end_date": now + timedelta(days=2), "expected": "S"
        },
        # A 级测试: 5星 + 绿标 + 充足时间
        {
            "desc": "A 级 (5星 + 绿标在编 + 时间充足)",
            "ml": 5, "bz": 1, "end_date": now + timedelta(days=10), "expected": "A"
        },
        # B 级测试 1: 4星硕博 + 绿标在编
        {
            "desc": "B 级 (4星公卫硕博 + 绿标在编)",
            "ml": 4, "bz": 1, "end_date": now + timedelta(days=10), "expected": "B"
        },
        # B 级测试 2: 5星 + 黄标备案制
        {
            "desc": "B 级 (5星预防医学 + 黄标备案制)",
            "ml": 5, "bz": 2, "end_date": now + timedelta(days=10), "expected": "B"
        },
        # C 级测试 1: 3星业务对口 + 绿标/黄标
        {
            "desc": "C 级 (3星业务对口 + 绿标在编)",
            "ml": 3, "bz": 1, "end_date": None, "expected": "C"
        },
        # C 级测试 2: 4星 + 黄标存疑
        {
            "desc": "C 级 (4星公卫学科 + 黄标存疑)",
            "ml": 4, "bz": 2, "end_date": None, "expected": "C"
        },
        # D 级测试 1: 2星模糊
        {
            "desc": "D 级 (2星模糊专业)",
            "ml": 2, "bz": 1, "end_date": None, "expected": "D"
        },
        # D 级测试 2: 1星排除
        {
            "desc": "D 级 (1星排除专业)",
            "ml": 1, "bz": 1, "end_date": None, "expected": "D"
        },
        # D 级测试 3: 红标非编合同工
        {
            "desc": "D 级 (红标非编劳务派遣)",
            "ml": 5, "bz": 0, "end_date": None, "expected": "D"
        }
    ]

    for c in cases:
        res = PriorityEvaluator.evaluate(
            match_level=c["ml"],
            is_bianzhi=c["bz"],
            apply_end_date=c["end_date"],
            now=now
        )
        assert res["priority_level"] == c["expected"], f"Priority Mismatch in {c['desc']}: expected {c['expected']}, got {res['priority_level']}"
        print(f"  - [{c['desc']}] -> 判定级别: {res['priority_level']}, 理由: {res['priority_reason']}")

    print("PriorityEvaluator 判定规则全部通过！(PASS)\n")

def test_job_deduplicator():
    print("=== 2. 多源岗位跨平台去重与相似度测试 (JobDeduplicator) ===")
    
    # 用例 1: 聚合源与官方源发布的同一岗位 (名称略微变体)
    job_official = {
        "province": "浙江省",
        "unit_name": "杭州市疾病预防控制中心",
        "job_name": "突发公共卫生事件应急处置岗",
        "education": "本科及以上"
    }
    job_aggregator = {
        "province": "浙江省",
        "unit_name": "杭州市疾控中心（市卫监所）",
        "job_name": "应急处置岗位（公卫医师）",
        "education": "本科及以上"
    }
    
    is_dup, sim, reason = JobDeduplicator.is_duplicate_job(job_official, job_aggregator)
    print(f"  - [跨源相似岗位比对] 是否为重复岗位: {is_dup}, 相似度得分: {sim:.2f}, 判定: {reason}")
    assert is_dup is True, "跨平台同岗位未识别出重复"

    # 用例 2: 不同单位的不同岗位
    job_other = {
        "province": "浙江省",
        "unit_name": "宁波市疾病预防控制中心",
        "job_name": "理化检验岗",
        "education": "硕士研究生"
    }
    is_dup2, sim2, reason2 = JobDeduplicator.is_duplicate_job(job_official, job_other)
    print(f"  - [不同单位岗位比对] 是否为重复岗位: {is_dup2}, 相似度得分: {sim2:.2f}, 判定: {reason2}")
    assert is_dup2 is False, "不同单位岗位误判为重复"

    print("JobDeduplicator 去重与相似度比对全部通过！(PASS)\n")

async def test_priority_service_and_db():
    print("=== 3. 优先级服务与数据库持久化测试 (PriorityService) ===")
    async with AsyncSessionLocal() as session:
        # 执行批量评定与回写
        stats = await PriorityService.run_batch_priority_evaluation(session)
        print("批量优先级评定统计:", stats)
        assert stats["status"] == "SUCCESS"
        assert stats["total_jobs"] > 0

        # 查询数据库中岗位的优先级字段
        res = await session.execute(select(Job))
        jobs = res.scalars().all()
        print(f"数据库中已持久化优先级岗位数: {len(jobs)}")
        for j in jobs:
            print(f"  - [{j.unit_name}] 岗位:{j.job_name} | 专业:{j.match_level}星 | 编制:{j.is_bianzhi} | 通知优先级:【{j.priority_level} 级】")
            assert j.priority_level in ("S", "A", "B", "C", "D")

    print("PriorityService 数据库持久化全部通过！(PASS)\n")

if __name__ == "__main__":
    test_priority_evaluator()
    test_job_deduplicator()
    asyncio.run(test_priority_service_and_db())
    print("🎉 Phase 7 所有测试用例 100% PASS！")
