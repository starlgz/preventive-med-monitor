import pytest
from app.extractors.deadline_detector import DeadlineDetector
from datetime import date, timedelta

def test_deadline_range_extraction():
    content = "报名时间为：2026年8月20日 09:00 至 2026年8月30日 17:00，逾期不再受理。"
    title = "2026年某疾控中心招聘公告"
    res = DeadlineDetector.extract_time_meta(title, content)
    assert res["start_date"] == date(2026, 8, 20)
    assert res["end_date"] == date(2026, 8, 30)
    assert res["is_expired"] is False

def test_expired_detection():
    content = "报名截止时间为2026年5月10日，请考生按时提交。"
    title = "2026年上半年招考"
    res = DeadlineDetector.extract_time_meta(title, content)
    assert res["end_date"] == date(2026, 5, 10)
    assert res["is_expired"] is True
    assert "已于" in res["expire_reason"]

def test_history_year_detection():
    content = "现将有关事项公告如下，报名时间另行通知。"
    title = "2024年某医院招聘聘用人员公告"
    res = DeadlineDetector.extract_time_meta(title, content)
    assert res["is_expired"] is True
    assert "往年历史公告" in res["expire_reason"]
