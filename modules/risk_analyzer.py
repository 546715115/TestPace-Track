from datetime import datetime
from modules.data_parser import normalize_progress

class RiskAnalyzer:
    def __init__(self, version_plans: list):
        self.version_plans = {vp['stage_name']: vp for vp in version_plans}

    def analyze_requirement(self, req: dict, current_date: str = None) -> list:
        """Analyze a single requirement for risks"""
        if current_date is None:
            current_date = datetime.now().strftime('%Y/%m/%d')

        risks = []

        # Check serial review (串讲/设计完成)
        if '需求串讲/设计完成' in self.version_plans:
            plan = self.version_plans['需求串讲/设计完成']
            if self._is_overdue(plan['target_date'], current_date):
                if req.get('串讲和测试设计进度') != '已完成':
                    risks.append('serial_review_incomplete')

        # Check reverse serial review (反串讲完成)
        if '需求反串讲完成' in self.version_plans:
            plan = self.version_plans['需求反串讲完成']
            if self._is_overdue(plan['target_date'], current_date):
                progress = normalize_progress(req.get('反串讲进度（%）', 0))
                if progress < 100:
                    risks.append('reverse_serial_incomplete')

        # Check test completion (测试完成)
        if '需求测试完成' in self.version_plans:
            plan = self.version_plans['需求测试完成']
            if self._is_overdue(plan['target_date'], current_date):
                progress = normalize_progress(req.get('测试进度', 0))
                if progress < 100:
                    risks.append('test_progress_delayed')

        # Check for empty required fields
        EMPTY_CHECK_FIELDS = ['测试人员', '计划转测时间', '测试进度']
        for field in EMPTY_CHECK_FIELDS:
            if not req.get(field):
                risks.append(f'empty_field_{field}')

        return risks

    def _is_overdue(self, target_date: str, current_date: str) -> bool:
        if not target_date or not current_date:
            return False
        return target_date < current_date