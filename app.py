from flask import Flask, jsonify, request, render_template
from modules.db_manager import init_db
from modules.version_manager import VersionManager
from modules.data_parser import ExcelReader, normalize_progress, parse_date
from modules.risk_analyzer import RiskAnalyzer
from modules.stats_calculator import StatsCalculator
import os
import json

app = Flask(__name__)

# Ensure DB is initialized
init_db()

def get_cache_file(version_id: str) -> str:
    """Find cache file for version_id"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
    if not os.path.exists(cache_dir):
        return None

    for filename in os.listdir(cache_dir):
        if version_id in filename and filename.endswith('.xlsx'):
            return os.path.join(cache_dir, filename)
    return None

def get_config_documents():
    """Load document configs"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'documents.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"documents": []}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/versions', methods=['GET'])
def get_versions():
    """Get all configured versions"""
    config = get_config_documents()
    return jsonify({'success': True, 'data': {'versions': config.get('documents', [])}})

@app.route('/api/sheets', methods=['GET'])
def get_sheets():
    version_id = request.args.get('version_id')
    if not version_id:
        return jsonify({'success': False, 'error': 'version_id required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        return jsonify({'success': False, 'error': 'No cache found. Please refresh.'})

    reader = ExcelReader(cache_file)
    sheets = reader.get_sheet_names()
    return jsonify({'success': True, 'data': {'sheets': sheets}})

@app.route('/api/load_sheet', methods=['POST'])
def load_sheet():
    data = request.json
    version_id = data.get('version_id')
    sheet_name = data.get('sheet_name')

    if not version_id or not sheet_name:
        return jsonify({'success': False, 'error': 'version_id and sheet_name required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        return jsonify({'success': False, 'error': 'No cache found'})

    reader = ExcelReader(cache_file)
    reader.load_sheet(sheet_name)

    groups = reader.get_requirement_groups()
    merged_reqs = [reader.merge_group(g) for g in groups]

    # Calculate risks
    version_plans = VersionManager().get_version_plans(version_id)
    analyzer = RiskAnalyzer(version_plans)

    for req in merged_reqs:
        req['risks'] = analyzer.analyze_requirement(req)

    # Calculate stats
    stats_calc = StatsCalculator(merged_reqs)
    stats = stats_calc.calculate_with_groups(groups)

    return jsonify({
        'success': True,
        'data': {
            'requirements': merged_reqs,
            'groups': groups,
            'stats': stats
        }
    })

@app.route('/api/requirements', methods=['GET'])
def get_requirements():
    version_id = request.args.get('version_id')
    sheet_name = request.args.get('sheet_name')

    if not version_id or not sheet_name:
        return jsonify({'success': False, 'error': 'version_id and sheet_name required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        return jsonify({'success': False, 'error': 'No cache found'})

    reader = ExcelReader(cache_file)
    reader.load_sheet(sheet_name)

    groups = reader.get_requirement_groups()
    merged_reqs = [reader.merge_group(g) for g in groups]

    # Calculate risks
    version_plans = VersionManager().get_version_plans(version_id)
    analyzer = RiskAnalyzer(version_plans)

    for req in merged_reqs:
        req['risks'] = analyzer.analyze_requirement(req)

    return jsonify({
        'success': True,
        'data': {
            'requirements': merged_reqs,
            'groups': groups
        }
    })

@app.route('/api/version_plans', methods=['GET'])
def get_version_plans():
    version_id = request.args.get('version_id')
    vm = VersionManager()
    plans = vm.get_version_plans(version_id)
    return jsonify({'success': True, 'data': {'plans': plans}})

@app.route('/api/version_plans', methods=['POST'])
def create_version_plan():
    data = request.json
    vm = VersionManager()
    plan_id = vm.create_version_plan(
        version_id=data.get('version_id'),
        version_name=data.get('version_name'),
        stage_name=data.get('stage_name'),
        target_date=data.get('target_date')
    )
    return jsonify({'success': True, 'data': {'plan_id': plan_id}})

@app.route('/api/version_plans/<int:plan_id>', methods=['PUT'])
def update_version_plan(plan_id):
    data = request.json
    vm = VersionManager()
    success = vm.update_version_plan(plan_id, data.get('target_date'))
    return jsonify({'success': success})

@app.route('/api/version_plans/<int:plan_id>', methods=['DELETE'])
def delete_version_plan(plan_id):
    vm = VersionManager()
    success = vm.delete_version_plan(plan_id)
    return jsonify({'success': success})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    version_id = request.args.get('version_id')
    sheet_name = request.args.get('sheet_name')

    if not version_id or not sheet_name:
        return jsonify({'success': False, 'error': 'version_id and sheet_name required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        return jsonify({'success': False, 'error': 'No cache found'})

    reader = ExcelReader(cache_file)
    reader.load_sheet(sheet_name)

    groups = reader.get_requirement_groups()
    merged_reqs = [reader.merge_group(g) for g in groups]

    stats_calc = StatsCalculator(merged_reqs)
    stats = stats_calc.calculate_with_groups(groups)

    return jsonify({'success': True, 'data': stats})

@app.route('/api/risks', methods=['GET'])
def get_risks():
    version_id = request.args.get('version_id')
    sheet_name = request.args.get('sheet_name')

    if not version_id or not sheet_name:
        return jsonify({'success': False, 'error': 'version_id and sheet_name required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        return jsonify({'success': False, 'error': 'No cache found'})

    reader = ExcelReader(cache_file)
    reader.load_sheet(sheet_name)

    groups = reader.get_requirement_groups()
    merged_reqs = [reader.merge_group(g) for g in groups]

    version_plans = VersionManager().get_version_plans(version_id)
    analyzer = RiskAnalyzer(version_plans)

    risks_by_type = {
        'not_started': [],
        'delayed': [],
        'empty_fields': []
    }

    for req in merged_reqs:
        req_risks = analyzer.analyze_requirement(req)
        for risk in req_risks:
            if risk == 'serial_review_incomplete' or risk == 'reverse_serial_incomplete':
                risks_by_type['not_started'].append(req)
            elif risk == 'test_progress_delayed':
                risks_by_type['delayed'].append(req)
            elif risk.startswith('empty_field_'):
                risks_by_type['empty_fields'].append(req)

    return jsonify({'success': True, 'data': risks_by_type})

if __name__ == '__main__':
    app.run(debug=True, port=5001)