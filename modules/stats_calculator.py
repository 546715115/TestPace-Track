from modules.data_parser import normalize_progress

class StatsCalculator:
    def __init__(self, requirements: list):
        self.requirements = requirements

    def calculate(self) -> dict:
        stats = {
            'total_requirements': len(self.requirements),
            'completed_count': 0,
            'in_progress_count': 0,
            'not_started_count': 0,
            'test_progress_distribution': {},
            'serial_review_status': {}
        }

        for req in self.requirements:
            progress = normalize_progress(req.get('测试进度', 0))

            if progress >= 100:
                stats['completed_count'] += 1
            elif progress > 0:
                stats['in_progress_count'] += 1
            else:
                stats['not_started_count'] += 1

            # Progress distribution buckets
            bucket = self._get_progress_bucket(progress)
            stats['test_progress_distribution'][bucket] = \
                stats['test_progress_distribution'].get(bucket, 0) + 1

            # Serial review status
            serial = req.get('串讲和测试设计进度', '未知')
            stats['serial_review_status'][serial] = \
                stats['serial_review_status'].get(serial, 0) + 1

        return stats

    def _get_progress_bucket(self, progress: int) -> str:
        if progress >= 100:
            return '100%'
        elif progress >= 75:
            return '75-99%'
        elif progress >= 50:
            return '50-74%'
        elif progress >= 25:
            return '25-49%'
        elif progress > 0:
            return '1-24%'
        else:
            return '0%'

    def calculate_with_groups(self, groups: list) -> dict:
        """Calculate stats including group information"""
        stats = self.calculate()

        merged_groups = [g for g in groups if g['is_merged']]
        single_rows = [g for g in groups if not g['is_merged']]

        stats['actual_requirement_count'] = len(groups)
        stats['total_row_count'] = sum(len(g['rows']) for g in groups)
        stats['merged_group_count'] = len(merged_groups)
        stats['single_row_count'] = len(single_rows)

        return stats