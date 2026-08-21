import asyncio
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.rules.bianzhi_service import BianzhiService
from app.core.database import AsyncSessionLocal
from app.models.entities import Job, Announcement
from sqlalchemy import select

def test_evaluator_rules():
    print("=== 1. 岗位编制三色判定规则算法测试 ===")
    test_cases = [
        # 绿标测试
        {
            "desc": "🟢 绿标: 疾控中心+实名编制",
            "job": "应急流调岗",
            "unit": "杭州市疾病预防控制中心",
            "unit_type": "疾控中心",
            "req": "纳入机构编制实名制管理，办理事业编制列编手续",
            "title": "2024年杭州市疾控中心公开招聘事业编制人员公告",
            "text": "本次招聘人员全部纳入财政全额拨款事业编制实名制管理",
            "expected_bianzhi": 1,
            "expected_type": "全额事业编"
        },
        {
            "desc": "🟢 绿标: 卫健委直属单位事业单位公开招聘",
            "job": "公共卫生医师",
            "unit": "绍兴市柯桥区卫生健康局",
            "unit_type": "卫健委/行政",
            "req": "全额拨款事业单位工作人员",
            "title": "绍兴市事业单位统一公开招聘工作人员公告",
            "text": "经人社局核准，面向社会公开招聘事业单位编制人员",
            "expected_bianzhi": 1,
            "expected_type": "全额事业编"
        },
        # 黄标测试 (备案制/员额制)
        {
            "desc": "🟡 黄标: 公立医院报备员额制",
            "job": "院感管理岗",
            "unit": "温州市中心医院",
            "unit_type": "综合医院/专科医院",
            "req": "实行公立医院报备员额制管理，享受同工同酬待遇",
            "title": "温州市中心医院公开招聘紧缺卫技人员公告",
            "text": "本次招考岗位实行公立医院改革员额备案制管理",
            "expected_bianzhi": 2,
            "expected_type": "报备员额"
        },
        {
            "desc": "🟡 黄标: 医院无明确编制说明 (黄标兜底)",
            "job": "临床流调医师",
            "unit": "宁波市第二医院",
            "unit_type": "综合医院/专科医院",
            "req": "具备执业医师资格证",
            "title": "宁波市第二医院招聘工作人员",
            "text": "面向社会公开招聘工作人员，待遇面议",
            "expected_bianzhi": 2,
            "expected_type": "报备员额"
        },
        # 红标测试 (非编/劳务派遣/合同制)
        {
            "desc": "🔴 红标: 疾控中心劳务派遣",
            "job": "采样助理岗",
            "unit": "台州市疾病预防控制中心",
            "unit_type": "疾控中心",
            "req": "签订劳务派遣劳动合同，缴纳五险一金",
            "title": "台州市疾控中心招聘劳务派遣人员公告",
            "text": "委托第三方人力资源公司办理劳务派遣手续，不列入编制",
            "expected_bianzhi": 0,
            "expected_type": "合同制"
        },
        {
            "desc": "🔴 红标: 编外聘用人员",
            "job": "公卫辅助人员",
            "unit": "金华市卫生健康委员会",
            "unit_type": "卫健委/行政",
            "req": "编外用工，合同制管理",
            "title": "金华市卫健委编外聘用人员招聘启事",
            "text": "本次招聘岗位为单位编外聘用人员",
            "expected_bianzhi": 0,
            "expected_type": "合同制"
        }
    ]

    for c in test_cases:
        res = BianzhiEvaluator.evaluate(
            job_name=c["job"],
            unit_name=c["unit"],
            unit_type=c["unit_type"],
            other_requirements=c["req"],
            announcement_title=c["title"],
            announcement_text=c["text"]
        )
        print(f"  - [{c['desc']}] is_bianzhi={res['is_bianzhi']}, 类型={res['bianzhi_type']}, 置信度={res['bianzhi_confidence']}, 证据={res['bianzhi_evidence']}")
        assert res["is_bianzhi"] == c["expected_bianzhi"], f"Error: expected is_bianzhi={c['expected_bianzhi']}, got {res['is_bianzhi']}"
        assert res["bianzhi_type"] == c["expected_type"], f"Error: expected bianzhi_type={c['expected_type']}, got {res['bianzhi_type']}"

    print("三色判定规则算法 100% 验证通过！(PASS)")

async def test_bianzhi_service():
    print("\n=== 2. 编制判定服务与数据库持久化测试 ===")
    async with AsyncSessionLocal() as session:
        # 执行批量评定
        stats = await BianzhiService.run_batch_evaluation(session)
        print("批量编制评定统计结果:", stats)
        assert stats["status"] == "SUCCESS"
        assert stats["total_jobs"] > 0

        # 查询数据库中岗位编制更新情况
        res = await session.execute(select(Job))
        jobs = res.scalars().all()
        print(f"数据库中已持久化编制岗位数: {len(jobs)}")
        for j in jobs:
            tag = "🟢 绿标(在编)" if j.is_bianzhi == 1 else ("🟡 黄标(存疑)" if j.is_bianzhi == 2 else "🔴 红标(非编)")
            print(f"  - [{j.unit_name}] 岗位:{j.job_name} | 标识:{tag} | 类型:{j.bianzhi_type} | 置信度:{j.bianzhi_confidence} | 证据:{j.bianzhi_evidence}")
            assert j.is_bianzhi is not None

    print("数据库编制持久化与更新全部通过！(PASS)")

if __name__ == "__main__":
    test_evaluator_rules()
    asyncio.run(test_bianzhi_service())
