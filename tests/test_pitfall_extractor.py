import pytest
from app.extractors.pitfall_extractor import PitfallExtractor

def test_service_years_and_penalty():
    text = "本次招聘岗位属于急需紧缺事业编，聘用人员在聘用单位最低服务年限为5年，服务期内不得调离或报考其他单位，提前离职需按规定承担违约责任并退还安家补贴。"
    res = PitfallExtractor.analyze(text)
    assert res["service_years"] == 5
    assert res["penalty_warning"] == 1
    assert res["risk_level"] == "HIGH"
    assert len(res["pitfalls"]) >= 2
    assert "最低服务年限长达 5 年" in res["pitfalls"][0]

def test_party_and_cert_requirement():
    text = "要求具有公共卫生执业医师资格，且必须为中共党员（含预备党员），具有规培合格证书。"
    res = PitfallExtractor.analyze(text)
    assert res["is_party_required"] == 1
    assert "公共卫生执业医师" in res["cert_requirement"]
    assert "规培" in res["training_requirement"]
    assert res["risk_level"] in ["MEDIUM", "HIGH"]

def test_age_relaxation():
    text = "年龄要求在35周岁以下，具有博士研究生学历或副高级专业技术职务任职资格人员年龄可放宽至45周岁。"
    res = PitfallExtractor.analyze(text)
    assert "35" in res["age_rules"]
    assert "45" in res["age_rules"]

def test_clean_job_no_pitfalls():
    text = "面向高校毕业生公开招聘公共卫生与预防医学专业技术人员，不限户籍，享受国家规定事业单位待遇。"
    res = PitfallExtractor.analyze(text)
    assert res["risk_level"] == "LOW"
    assert res["service_years"] is None
    assert len(res["pitfalls"]) == 0
