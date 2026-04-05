from modules.db_manager import get_db

class VersionManager:
    def create_version_plan(self, version_id: str, version_name: str,
                           stage_name: str, target_date: str) -> int:
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

    def get_version_plans(self, version_id: str = None) -> list:
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
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM version_plan WHERE id = ?', (plan_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success