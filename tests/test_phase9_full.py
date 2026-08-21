import asyncio
import os
import sys
import json
from datetime import datetime

from app.filters.filter_engine import UserFilterEngine
from app.filters.filter_service import UserFilterService
from app.core.database import AsyncSessionLocal
from app.models.entities import Job, UserFilter
from sqlalchemy import select

async def main():
    print("=== 1. 用户个性化画像过滤引擎测试 (UserFilterEngine) ===")
    
    # 模拟一个岗位
    sample_job = {
        "province": "浙江省",
        "unit_name": "杭州市疾病预防控制中心",
        "unit_type": "疾控中心",
        "match_level": 5,
        "is_bianzhi": 1,
        "education": "本科及以上",
        "is_fresh_grad": 1,  # 限应届
        "cert_requirements": "公共卫生执业医师资格证",
        "age_limit_num": 35
    }

    # 用例 1: 完全符合画像 (应届 + 本科 + 有证书 + 浙江 + 在编)
    user_conf_1 = {
        "provinces": ["浙江省", "上海市"],
        "min_star": 4,
        "only_bianzhi": True,
        "include_beian": True,
        "education_level": "本科",
        "is_fresh_grad": True,
        "has_cert": True,
        "max_age": 28,
        "unit_types": ["疾控中心"]
    }
    res1 = UserFilterEngine.match_job(sample_job, user_conf_1)
    print(f"  - [用例1: 完美匹配画像] 匹配结果: {res1['matched']}, 原因: {res1['reason']}")
    assert res1["matched"] is True

    # 用例 2: 省份不符 (期望江苏)
    user_conf_2 = dict(user_conf_1, provinces=["江苏省"])
    res2 = UserFilterEngine.match_job(sample_job, user_conf_2)
    print(f"  - [用例2: 省份过滤] 匹配结果: {res2['matched']}, 原因: {res2['reason']}")
    assert res2["matched"] is False

    # 用例 3: 往届生过滤 (岗位限应届，用户为往届生)
    user_conf_3 = dict(user_conf_1, is_fresh_grad=False)
    res3 = UserFilterEngine.match_job(sample_job, user_conf_3)
    print(f"  - [用例3: 应届要求过滤] 匹配结果: {res3['matched']}, 原因: {res3['reason']}")
    assert res3["matched"] is False

    # 用例 4: 无执业医师证书 (岗位强制要求证书)
    user_conf_4 = dict(user_conf_1, has_cert=False)
    res4 = UserFilterEngine.match_job(sample_job, user_conf_4)
    print(f"  - [用例4: 证书要求过滤] 匹配结果: {res4['matched']}, 原因: {res4['reason']}")
    assert res4["matched"] is False

    # 用例 5: 年龄超限 (用户 38 岁，岗位限 35 岁)
    user_conf_5 = dict(user_conf_1, max_age=38)
    res5 = UserFilterEngine.match_job(sample_job, user_conf_5)
    print(f"  - [用例5: 年龄超限过滤] 匹配结果: {res5['matched']}, 原因: {res5['reason']}")
    assert res5["matched"] is False

    print("UserFilterEngine 所有画像过滤用例全部通过！(PASS)")

    print("\n=== 2. 用户订阅管理与数据库持久化测试 (UserFilterService) ===")
    async with AsyncSessionLocal() as session:
        # 创建用户订阅规则
        test_user = "telegram:6213715919"
        rules = {
            "provinces": ["浙江省"],
            "min_star": 4,
            "only_bianzhi": True,
            "education_level": "本科"
        }
        filter_obj = await UserFilterService.create_user_filter(
            session=session,
            user_id=test_user,
            filter_name="浙江疾控在编订阅",
            rules=rules
        )
        print(f"创建订阅规则成功: ID={filter_obj.id}, 用户={filter_obj.user_id}, 规则名={filter_obj.filter_name}")
        assert filter_obj.id is not None

        # 验证数据库中持久化的用户规则
        res = await session.execute(select(UserFilter).where(UserFilter.user_id == test_user))
        records = res.scalars().all()
        print(f"数据库中查到用户 [{test_user}] 的规则数: {len(records)}")
        for r in records:
            print(f"  - 规则名:{r.filter_name}, 目标省份:{r.target_provinces}, 最低星级:{r.min_match_level}")

        # 比对岗位与用户画像
        job_stmt = select(Job).limit(1)
        job = (await session.execute(job_stmt)).scalars().first()
        if job:
            match_res = await UserFilterService.match_user_and_job(
                session=session,
                user_id=test_user,
                job_id=job.id
            )
            print(f"\n岗位 [{job.unit_name} - {job.job_name}] 与用户订阅匹配测试:")
            print(f"  - 匹配状态: {match_res['matched']}")
            print(f"  - 匹配详情: {match_res['reason']}")

    print("\n🎉 Phase 9 所有测试用例 100% PASS！")

if __name__ == "__main__":
    asyncio.run(main())
