# tests/test_stats_calculator.py
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.stats_calculator import StatsCalculator

def test_calc_requirement_stats():
    requirements = [
        {'测试进度': 100, '串讲和测试设计进度': '已完成'},
        {'测试进度': 50, '串讲和测试设计进度': '进行中'},
        {'测试进度': 0, '串讲和测试设计进度': '未开始'},
    ]

    calc = StatsCalculator(requirements)
    stats = calc.calculate()

    assert stats['total_requirements'] == 3
    assert stats['completed_count'] == 1
    assert stats['in_progress_count'] == 1
    assert stats['not_started_count'] == 1

def test_progress_distribution():
    requirements = [
        {'测试进度': 100},
        {'测试进度': 80},
        {'测试进度': 50},
        {'测试进度': 20},
        {'测试进度': 0},
    ]

    calc = StatsCalculator(requirements)
    stats = calc.calculate()

    assert stats['test_progress_distribution']['100%'] == 1
    assert stats['test_progress_distribution']['75-99%'] == 1
    assert stats['test_progress_distribution']['50-74%'] == 1
    assert stats['test_progress_distribution']['1-24%'] == 1
    assert stats['test_progress_distribution']['0%'] == 1