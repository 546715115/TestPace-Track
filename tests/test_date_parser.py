# tests/test_date_parser.py
import pytest
import sys
sys.path.insert(0, '..')
from modules.data_parser import ExcelReader, parse_date, normalize_progress

def test_date_parsing():
    from modules.data_parser import parse_date
    from datetime import datetime
    current_year = datetime.now().year
    assert parse_date('2024/4/1') == '2024/04/01'
    assert parse_date('2024.4.1') == '2024/04/01'
    assert parse_date('4/1') == f'{current_year}/04/01'
    assert parse_date('4.1') == f'{current_year}/04/01'

def test_progress_normalization():
    from modules.data_parser import normalize_progress
    assert normalize_progress('已完成') == 100
    assert normalize_progress(80) == 80
    assert normalize_progress('50%') == 50
    assert normalize_progress('') == 0