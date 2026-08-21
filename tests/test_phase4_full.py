import asyncio, os, sys
from datetime import datetime
from app.extractors.unit_type_classifier import UnitTypeClassifier
from app.extractors.eligibility_extractor import EligibilityExtractor
from app.extractors.pipeline import ExtractionPipeline
from app.extractors.service import JobExtractionService
from app.core.database import AsyncSessionLocal
from app.models.entities import Announcement, Job, Source
from sqlalchemy import select, delete

async def test_full_phase4():
    print("=== 1. 测试单位类型智能分类器 (UnitTypeClassifier) ===")
    assert UnitTypeClassifier.classify("浙江省疾病预防控制中心") == "疾控中心"
    assert UnitTypeClassifier.classify("杭州市卫生健康委员会") == "卫健局/委"
    assert UnitTypeClassifier.classify("宁波市第一医院") == "公立医院"
    assert UnitTypeClassifier.classify("浙江省医学科学院") == "科研院所"
    assert UnitTypeClassifier.classify("温州市妇幼保健院") == "妇幼保健院"
    print("UnitTypeClassifier 分类全部准确！(PASS)")

    print("\n=== 2. 测试报考画像四维特征提取器 (EligibilityExtractor) ===")
    raw_text = "要求公共卫生执业医师资格，需取得住院医师规范化培训合格证书。限应届毕业生报考，年龄35周岁以下（1991年1月1日以后出生），要求浙江省户籍。"
    el = EligibilityExtractor.extract_all(
        major_text="预防医学",
        education_text="本科及以上",
        other_text=raw_text,
        full_text=raw_text
    )
    print(f"提取结果: cert={el['cert_requirements']}, training={el['is_training_required']}, fresh={el['is_fresh_grad']}, age={el['age_limit_num']}, residency={el['residency_limit']}")
    assert "公共卫生执业医师" in el['cert_requirements']
    assert el['is_training_required'] == 1
    assert el['is_fresh_grad'] == 1
    assert el['age_limit_num'] == 35
    assert "浙江省" in el['residency_limit']
    print("EligibilityExtractor 画像提取全部精准！(PASS)")

    print("\n=== 3. 测试端到端结构化入库与去重持久化 (JobExtractionService) ===")
    async with AsyncSessionLocal() as session:
        # 清理旧测试数据
        await session.execute(delete(Job))
        await session.execute(delete(Announcement))
        await session.execute(delete(Source))
        await session.commit()

        # 插入测试源与测试公告 (含 HTML 岗位表)
        src = Source(source_id="test_zj", name="浙江省测试源", category="official", province="浙江", base_url="http://test", driver_type="http")
        session.add(src)
        await session.commit()
        await session.refresh(src)

        html_body = """
        <div>
            <h2>2026年浙江省疾病预防控制中心公开招聘高层次人才公告</h2>
            <p>报名时间：2026-09-01 至 2026-09-10。本次招聘纳入事业单位编制管理。</p>
            <table>
                <tr>
                    <th>序号</th><th>用人单位</th><th>岗位名称</th><th>招聘人数</th><th>专业要求</th><th>学历要求</th><th>其他条件</th>
                </tr>
                <tr>
                    <td>JK01</td><td>浙江省疾病预防控制中心</td><td>应急处置岗</td><td>2</td><td>预防医学、公共卫生</td><td>本科及以上</td><td>需取得公卫执业医师证，年龄30周岁以下</td>
                </tr>
                <tr>
                    <td>JK02</td><td>浙江省疾病预防控制中心</td><td>流病监测岗</td><td>1</td><td>流行病与卫生统计学</td><td>硕士研究生</td><td>要求限2026年应届毕业生</td>
                </tr>
            </table>
        </div>
        """
        ann = Announcement(
            source_id=src.id,
            title="2026年浙江省疾病预防控制中心公开招聘高层次人才公告",
            url="http://test/ann_phase4_01",
            content_raw=html_body,
            publish_date=datetime.now()
        )
        session.add(ann)
        await session.commit()
        await session.refresh(ann)

        # 执行结构化提取
        res = await JobExtractionService.extract_and_save_jobs(session, ann.id)
        print(f"提取状态: {res['status']}, 提取岗位数: {res['total_extracted']}, 新入库数: {res['new_saved']}")
        assert res["total_extracted"] == 2 and res["new_saved"] == 2

        # 验证 SQLite 物理表中的持久化字段
        stmt = select(Job).where(Job.announcement_id == ann.id)
        db_jobs = (await session.execute(stmt)).scalars().all()
        print(f"数据库中查到岗位数: {len(db_jobs)}")
        for j in db_jobs:
            print(f"  - [{j.unit_name} - {j.unit_type}] 岗位:{j.job_name}, 人数:{j.headcount}, 学历:{j.education}, 年龄:{j.age_limit_num}, 证书:{j.cert_requirements}, 应届:{j.is_fresh_grad}, UID:{j.job_uid[:16]}...")
            assert j.unit_type == "疾控中心"
            assert j.province == "浙江"
            assert j.job_uid is not None

        # 再次执行结构化提取，验证去重不重复插入
        res_repeat = await JobExtractionService.extract_and_save_jobs(session, ann.id)
        print(f"重复提取测试: new_saved={res_repeat['new_saved']}, updated={res_repeat['updated']}")
        assert res_repeat["new_saved"] == 0 and res_repeat["updated"] == 2
        print("端到端持久化与去重机制全部通过！(PASS)")

if __name__ == "__main__":
    asyncio.run(test_full_phase4())
