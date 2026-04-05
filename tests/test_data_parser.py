# tests/test_data_parser.py
import pytest
import sys
sys.path.insert(0, '..')
from modules.data_parser import ExcelReader

def test_read_sheet_names():
    reader = ExcelReader('copy_new.xlsx')
    sheets = reader.get_sheet_names()
    assert '0330需求列表' in sheets