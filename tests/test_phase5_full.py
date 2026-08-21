import asyncio
from app.rules.major_matcher import MajorMatcher
from app.rules.matcher_service import MajorMatcherService
from app.core.database import AsyncSessionLocal
from app.models.entities import Job

def test_matcher_rules():
    print("=== 1. 五星专业匹配规则算法测试 ===")
    
    test_cases = [
        # (专业文本, 单位类型, 岗位名称, 期望星级, 描述)
        ("预防医学", "疾控中心", "业务科", 5, "5星: 明确命中预防医学"),
        ("公共卫生医师（100401）", "卫生监督", "监督员", 5, "5星: 命中代码与医师"),
        ("卫生检验与检疫", "疾控中心", "理化检验", 5, "5星: 命中本科国控专业"),
        ("流行病与卫生统计学", "科研院所", "研究岗", 4, "4星: 命中公卫二级学科"),
        ("公共卫生与预防医学、公共卫生硕士", "疾控中心", "慢病所", 4, "4星: 命中一级学科与专硕"),
        ("公共卫生类", "疾控中心", "流调员", 3, "3星: 疾控中心+公卫大类"),
        ("医学类（不限具体专业）", "疾控中心", "应急处置岗", 3, "3星: 疾控中心+业务岗+医学大类"),
        ("临床医学及相关专业", "综合医院/专科医院", "医师", 2, "2星: 医院大类待核实"),
        ("中医学、中西医结合", "综合医院/专科医院", "中医科", 1, "1星: 明确非公卫专业排除"),
        ("计算机科学与技术、会计学", "疾控中心", "网络管理员", 1, "1星: 明确非医学专业排除"),
    ]

    for major, unit_type, job_name, expected_level, desc in test_cases:
        res = MajorMatcher.match(major_raw=major, unit_type=unit_type, job_name=job_name)
        actual = res["match_level"]
        print(f"  - [{desc}] 匹配星级: {actual}星, 理由: {res['match_reason']}")
        assert actual == expected_level, f"Failed: {desc} expected {expected_level}, got {actual}"
    print("五星专业匹配算法全部通过！(PASS)")

async def test_matcher_service():
    print("\n=== 2. 专业匹配服务与数据库持久化测试 ===")
    async with AsyncSessionLocal() as session:
        # 1. 批量计算并更新
        batch_res = await MajorMatcherService.run_batch_match(session)
        print("批量打分结果:", batch_res)
        assert batch_res["status"] == "SUCCESS"

        # 2. 验证数据库中是否成功打上星级
        jobs = (await session.execute(Job.__table__.select())).fetchall()
        print(f"数据库中岗位打分情况 (总计 {len(jobs)} 条):")
        for j in jobs:
            print(f"  - [{j.unit_name}] 岗位:{j.job_name}, 专业:{j.major_raw}, 星级:{j.match_level}星, 命中代码:{j.matched_major_codes}")
            assert j.match_level is not None and j.match_level > 0

    print("数据库持久化与打分更新全部通过！(PASS)")

if __name__ == "__main__":
    test_matcher_rules()
    asyncio.run(test_matcher_service())
