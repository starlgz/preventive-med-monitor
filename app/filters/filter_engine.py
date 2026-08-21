from typing import Dict, Any, List, Optional
import json
from loguru import logger

class UserFilterEngine:
    """多用户个性化订阅画像匹配与过滤器"""

    @staticmethod
    def match_job(job_data: Dict[str, Any], filter_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        判断岗位是否符合用户的个性化订阅画像
        
        filter_config 字段结构:
        {
            "provinces": ["浙江省", "江苏省"],        # 期望省份列表 (空则不限)
            "min_star": 4,                           # 最低专业匹配星级 (1-5, 默认3)
            "only_bianzhi": True,                    # 是否仅要事业编制 (is_bianzhi == 1)
            "include_beian": True,                   # 若 only_bianzhi 为 True，是否包含备案制 (is_bianzhi in (1, 2))
            "education_level": "本科",                # 用户最高学历 ("大专", "本科", "硕士", "博士")
            "is_fresh_grad": True,                   # 用户是否为应届毕业生 (True: 可报应届岗和不限岗; False: 可报往届岗和不限岗)
            "has_cert": True,                        # 用户是否已取得执业医师证 (False 则过滤强制要求证书的岗位)
            "max_age": 35,                           # 用户实际年龄 (过滤年龄上限小于该值的岗位)
            "unit_types": ["疾控中心", "妇幼保健"]    # 期望单位类型列表 (空则不限)
        }
        """
        reasons = []
        is_matched = True

        # 1. 省份过滤
        allowed_provinces = filter_config.get("provinces") or []
        if allowed_provinces:
            job_prov = job_data.get("province") or ""
            if not any(p in job_prov or job_prov in p for p in allowed_provinces):
                return {
                    "matched": False,
                    "reason": f"省份不匹配 (岗位省份:{job_prov}, 订阅省份:{allowed_provinces})"
                }

        # 2. 单位类型过滤
        allowed_unit_types = filter_config.get("unit_types") or []
        if allowed_unit_types:
            unit_type = job_data.get("unit_type") or "其他事业单位"
            if unit_type not in allowed_unit_types:
                return {
                    "matched": False,
                    "reason": f"单位类型不匹配 (岗位类型:{unit_type}, 订阅类型:{allowed_unit_types})"
                }

        # 3. 最低专业匹配星级
        min_star = filter_config.get("min_star", 3)
        job_star = job_data.get("match_level") or 1
        if job_star < min_star:
            return {
                "matched": False,
                "reason": f"专业匹配度不足 (岗位:{job_star}星, 最低要求:{min_star}星)"
            }
        reasons.append(f"专业匹配{job_star}星")

        # 4. 编制性质过滤
        only_bianzhi = filter_config.get("only_bianzhi", False)
        include_beian = filter_config.get("include_beian", True)
        job_bianzhi = job_data.get("is_bianzhi", 0)

        if only_bianzhi:
            if include_beian:
                # 允许在编(1) 和 备案制/存疑(2)
                if job_bianzhi not in (1, 2):
                    return {
                        "matched": False,
                        "reason": f"非事业编制或备案制岗位 (is_bianzhi={job_bianzhi})"
                    }
            else:
                # 仅允许纯事业在编(1)
                if job_bianzhi != 1:
                    return {
                        "matched": False,
                        "reason": f"非实名事业编制岗位 (is_bianzhi={job_bianzhi})"
                    }
        reasons.append(f"编制标识={job_bianzhi}")

        # 5. 学历门槛过滤
        user_edu = filter_config.get("education_level")
        job_edu = job_data.get("education") or ""
        edu_rank = {"大专": 1, "专科": 1, "本科": 2, "学士": 2, "硕士": 3, "研究生": 3, "博士": 4}
        
        if user_edu and user_edu in edu_rank:
            u_rank = edu_rank[user_edu]
            # 检查岗位最低学历
            req_rank = 0
            if "博士" in job_edu:
                req_rank = 4
            elif "硕士" in job_edu or "研究生" in job_edu:
                req_rank = 3
            elif "本科" in job_edu or "学士" in job_edu:
                req_rank = 2
            elif "大专" in job_edu or "专科" in job_edu:
                req_rank = 1

            if req_rank > u_rank:
                return {
                    "matched": False,
                    "reason": f"学历门槛不符 (岗位要求:{job_edu}, 用户学历:{user_edu})"
                }
            reasons.append(f"学历符合({user_edu}>={job_edu})")

        # 6. 应届生要求过滤
        # job.is_fresh_grad: 1-限应届, 2-限往届/有经验, 0-不限
        user_is_fresh = filter_config.get("is_fresh_grad")
        job_fresh = job_data.get("is_fresh_grad", 0)

        if user_is_fresh is not None:
            if user_is_fresh is True and job_fresh == 2:
                return {
                    "matched": False,
                    "reason": "岗位限往届/工作经验，用户为应届生"
                }
            elif user_is_fresh is False and job_fresh == 1:
                return {
                    "matched": False,
                    "reason": "岗位仅限应届毕业生，用户为往届生"
                }

        # 7. 执业资格证书过滤
        user_has_cert = filter_config.get("has_cert")
        cert_req = job_data.get("cert_requirements") or ""
        # 如果岗位强制要求证书，但用户没有证书
        if user_has_cert is False:
            if cert_req and cert_req != "无明确证书限制" and ("执业" in cert_req or "资格证" in cert_req):
                return {
                    "matched": False,
                    "reason": f"岗位强制要求执业证书({cert_req})，用户未取得"
                }

        # 8. 年龄上限过滤
        user_age = filter_config.get("max_age")
        job_age_limit = job_data.get("age_limit_num")
        if user_age and job_age_limit:
            if user_age > job_age_limit:
                return {
                    "matched": False,
                    "reason": f"用户年龄({user_age}岁)超过岗位上限({job_age_limit}岁)"
                }

        return {
            "matched": True,
            "reason": " | ".join(reasons)
        }
