# tests/test_version_manager.py
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.version_manager import VersionManager

def test_create_and_get_version_plan():
    vm = VersionManager()
    plan_id = vm.create_version_plan(
        version_id='0330',
        version_name='Beta_T1',
        stage_name='需求串讲/设计完成',
        target_date='2024/03/15'
    )
    assert plan_id > 0

    plans = vm.get_version_plans('0330')
    assert len(plans) > 0
    assert plans[0]['stage_name'] == '需求串讲/设计完成'