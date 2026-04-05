# tests/test_risk_analyzer.py
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.risk_analyzer import RiskAnalyzer

def test_risk_serial_review_incomplete():
    plans = [{'stage_name': '需求串讲/设计完成', 'target_date': '2024/03/01'}]
    requirement = {'串讲和测试设计进度': '进行中', '测试进度': 50}

    analyzer = RiskAnalyzer(plans)
    risks = analyzer.analyze_requirement(requirement, current_date='2024/03/15')
    assert 'serial_review_incomplete' in risks

def test_no_risk_when_completed():
    plans = [{'stage_name': '需求串讲/设计完成', 'target_date': '2024/03/01'}]
    requirement = {'串讲和测试设计进度': '已完成', '测试进度': 100, '测试人员': '张三', '计划转测时间': '2024/03/20'}

    analyzer = RiskAnalyzer(plans)
    risks = analyzer.analyze_requirement(requirement, current_date='2024/03/15')
    assert len(risks) == 0

def test_empty_field_risk():
    plans = []
    requirement = {'测试人员': '', '测试进度': 0}

    analyzer = RiskAnalyzer(plans)
    risks = analyzer.analyze_requirement(requirement, current_date='2024/03/15')
    assert 'empty_field_测试人员' in risks