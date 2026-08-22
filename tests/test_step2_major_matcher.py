import pytest
from app.rules.major_matcher import MajorMatcher

def test_level_5_exact_major():
    """测试 5 星：明确预防医学/国标代码/MPH"""
    # 本科国标代码
    res = MajorMatcher.calculate_match_score("100401K 预防医学", "疾控中心", "公卫医师", "某市疾病预防控制中心")
    assert res["match_level"] == 5
    assert "100401K" in res["matched_codes"]
    assert res["match_score"] >= 85

    # 研究生 MPH
    res2 = MajorMatcher.calculate_match_score("公共卫生硕士(MPH)", "疾控中心", "慢病防控专员", "某省疾控中心")
    assert res2["match_level"] == 5
    assert "公共卫生硕士" in str(res2["matched_keywords"])

def test_level_4_sub_disciplines():
    """测试 4 星：二级学科流统、卫检、毒理、环卫"""
    res = MajorMatcher.calculate_match_score("流行病与卫生统计学、卫生毒理学", "综合医院", "科研助理", "某大学附属医院")
    assert res["match_level"] == 4
    assert res["match_score"] >= 68

def test_logic_exclusion_negation():
    """测试 AST 逻辑消歧：识别否定排除词"""
    # 明确排除公卫
    res = MajorMatcher.calculate_match_score("临床医学(除预防医学外)", "综合医院", "外科医师", "市人民医院")
    assert res["match_level"] == 1
    assert "否定排除" in res["evidence_chain"][0] or "排除" in res["match_reason"]

    # 包含不含预防
    res2 = MajorMatcher.calculate_match_score("基础医学（不含公卫）", "综合医院", "病理科医师", "市人民医院")
    assert res2["match_level"] == 1

def test_cdc_job_weight_bonus():
    """测试 CDC 核心单位与岗位权重加成"""
    # 岗位名称是流调，即使专业写了医学类，也能提升
    res = MajorMatcher.calculate_match_score("医学类", "疾控中心", "现场流调与应急处置", "区疾控中心")
    assert res["match_level"] >= 3
    assert res["match_score"] >= 60
