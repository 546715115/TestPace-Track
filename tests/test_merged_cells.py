# tests/test_merged_cells.py
import pytest
import sys
sys.path.insert(0, '..')
from modules.data_parser import ExcelReader

def test_requirement_groups_from_col_a():
    reader = ExcelReader('copy_new.xlsx')
    reader.load_sheet('0330需求列表')
    groups = reader.get_requirement_groups()
    # There should be groups based on column A merges
    assert len(groups) > 0
    assert groups[0]['is_merged'] in [True, False]

def test_merge_group():
    reader = ExcelReader('copy_new.xlsx')
    reader.load_sheet('0330需求列表')
    groups = reader.get_requirement_groups()
    assert len(groups) > 0
    merged = reader.merge_group(groups[0])
    assert isinstance(merged, dict)
    assert '_rows' in merged