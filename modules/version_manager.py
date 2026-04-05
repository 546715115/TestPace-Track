"""
版本计划管理模块
版本计划 CRUD 操作
"""
from typing import List, Dict, Optional

from modules.db_manager import get_db


class VersionManager:
    """版本计划管理器"""

    def create_version_plan(self, version_id: str, version_name: str,
                           stage_name: str, target_date: str) -> int:
        """创建版本计划"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO version_plan (version_id, version_name, stage_name, target_date)
            VALUES (?, ?, ?, ?)
        ''', (version_id, version_name, stage_name, target_date))
        conn.commit()
        plan_id = cursor.lastrowid
        conn.close()
        return plan_id

    def get_version_plans(self, version_id: str = None) -> List[Dict]:
        """获取版本计划列表"""
        conn = get_db()
        cursor = conn.cursor()

        if version_id:
            cursor.execute('''
                SELECT * FROM version_plan WHERE version_id = ?
                ORDER BY version_name, id
            ''', (version_id,))
        else:
            cursor.execute('SELECT * FROM version_plan ORDER BY version_name, id')

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_version_plan(self, plan_id: int, target_date: str) -> bool:
        """更新版本计划"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE version_plan SET target_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (target_date, plan_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    def delete_version_plan(self, plan_id: int) -> bool:
        """删除版本计划"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM version_plan WHERE id = ?', (plan_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    def get_versions_by_name(self, version_name: str) -> List[Dict]:
        """按版本名称获取计划"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM version_plan WHERE version_name = ?
            ORDER BY id
        ''', (version_name,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


if __name__ == '__main__':
    # 测试代码
    vm = VersionManager()
    plans = vm.get_version_plans()
    print(f"Current plans: {plans}")

    # 创建测试计划
    plan_id = vm.create_version_plan(
        version_id='0330',
        version_name='Beta_T1',
        stage_name='需求串讲/设计完成',
        target_date='2026/03/15'
    )
    print(f"Created plan ID: {plan_id}")
