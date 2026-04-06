"""
TestPace-Track Flask 后端
测试进度跟踪工具 API
"""
import os
import json
from flask import Flask, jsonify, request, render_template

from modules.db_manager import init_db
from modules.version_manager import VersionManager
from modules.data_parser import ExcelReader
from modules.risk_analyzer import RiskAnalyzer
from modules.stats_calculator import StatsCalculator, EMPTY_FIELD_COLUMNS
from modules.data_fetcher import DataFetcher

app = Flask(__name__)

# 初始化数据库
init_db()


def get_cache_file(version_id: str) -> str:
    """查找版本对应的缓存文件"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
    if not os.path.exists(cache_dir):
        return None

    for filename in os.listdir(cache_dir):
        if version_id in filename and filename.endswith('.xlsx'):
            return os.path.join(cache_dir, filename)
    return None


def get_config_documents():
    """加载文档配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'documents.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"documents": []}


def save_config_documents(config):
    """保存文档配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'documents.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_cookie_config():
    """加载Cookie配置"""
    cookie_path = os.path.join(os.path.dirname(__file__), 'config', 'cookies.json')
    if os.path.exists(cookie_path):
        with open(cookie_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"cookie": ""}


def save_cookie_config(cookie):
    """保存Cookie配置"""
    cookie_path = os.path.join(os.path.dirname(__file__), 'config', 'cookies.json')
    with open(cookie_path, 'w', encoding='utf-8') as f:
        json.dump({"cookie": cookie}, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    return render_template('index.html')


# ============ 版本和文档 API ============

@app.route('/api/versions', methods=['GET'])
def get_versions():
    """获取所有版本配置"""
    config = get_config_documents()
    return jsonify({'success': True, 'data': {'versions': config.get('documents', [])}})


@app.route('/api/documents', methods=['GET'])
def get_documents():
    """获取文档配置列表"""
    config = get_config_documents()
    return jsonify({'success': True, 'data': {'documents': config.get('documents', [])}})


@app.route('/api/documents', methods=['POST'])
def create_document():
    """创建/更新文档配置"""
    data = request.json
    config = get_config_documents()

    new_doc = {
        'version_id': data.get('version_id'),
        'name': data.get('name'),
        'bucket_path': data.get('bucket_path'),
        'doc_id': data.get('doc_id')
    }

    # 检查是否已存在
    for i, doc in enumerate(config.get('documents', [])):
        if doc.get('version_id') == new_doc['version_id']:
            config['documents'][i] = new_doc
            save_config_documents(config)
            return jsonify({'success': True, 'data': {'document': new_doc}})

    config.setdefault('documents', []).append(new_doc)
    save_config_documents(config)
    return jsonify({'success': True, 'data': {'document': new_doc}})


@app.route('/api/documents/<version_id>', methods=['PUT'])
def update_document(version_id):
    """更新文档配置"""
    data = request.json
    config = get_config_documents()

    for i, doc in enumerate(config.get('documents', [])):
        if doc.get('version_id') == version_id:
            config['documents'][i] = {
                'version_id': version_id,
                'name': data.get('name', doc.get('name')),
                'bucket_path': data.get('bucket_path', doc.get('bucket_path')),
                'doc_id': data.get('doc_id', doc.get('doc_id'))
            }
            save_config_documents(config)
            return jsonify({'success': True, 'data': {'document': config['documents'][i]}})

    return jsonify({'success': False, 'error': 'Document not found'})


@app.route('/api/documents/<version_id>', methods=['DELETE'])
def delete_document(version_id):
    """删除文档配置"""
    config = get_config_documents()

    for i, doc in enumerate(config.get('documents', [])):
        if doc.get('version_id') == version_id:
            del config['documents'][i]
            save_config_documents(config)
            return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Document not found'})


# ============ Cookie 配置 API ============

@app.route('/api/cookie', methods=['GET'])
def get_cookie():
    """获取Cookie配置状态"""
    config = get_cookie_config()
    has_cookie = bool(config.get('cookie', '').strip())
    return jsonify({'success': True, 'data': {'configured': has_cookie}})


@app.route('/api/cookie', methods=['POST'])
def save_cookie():
    """保存Cookie配置"""
    data = request.json
    cookie = data.get('cookie', '')
    save_cookie_config(cookie)
    return jsonify({'success': True})


# ============ Sheet 和数据 API ============

@app.route('/api/sheets', methods=['GET'])
def get_sheets():
    """获取版本对应的所有 Sheet 页"""
    version_id = request.args.get('version_id')
    if not version_id:
        return jsonify({'success': False, 'error': 'version_id required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        return jsonify({'success': False, 'error': 'No cache found. Please download first.'})

    reader = ExcelReader(cache_file)
    sheets = reader.get_sheet_names()
    return jsonify({'success': True, 'data': {'sheets': sheets}})


@app.route('/api/download', methods=['POST'])
def download_document():
    """从 OneBox API 下载文档"""
    data = request.json
    version_id = data.get('version_id')

    if not version_id:
        return jsonify({'success': False, 'error': 'version_id required'})

    # 获取文档配置
    config = get_config_documents()
    doc = None
    for d in config.get('documents', []):
        if d.get('version_id') == version_id:
            doc = d
            break

    if not doc:
        return jsonify({'success': False, 'error': '文档配置不存在'})

    try:
        fetcher = DataFetcher()
        cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
        os.makedirs(cache_dir, exist_ok=True)

        save_path = fetcher.save_to_cache(
            bucket_path=doc.get('bucket_path'),
            doc_id=doc.get('doc_id'),
            version_name=doc.get('name', version_id),
            cache_dir=cache_dir
        )

        if save_path:
            return jsonify({'success': True, 'data': {'cache_path': save_path}})
        else:
            return jsonify({'success': False, 'error': '下载失败，请检查配置'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'下载异常: {str(e)}'})


@app.route('/api/load_sheet', methods=['POST'])
def load_sheet():
    """加载指定 Sheet 的数据"""
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

    # 获取原始所有行（用于前端rowspan合并显示）
    raw_rows, groups = reader.get_raw_rows()

    # 计算风险：先对每个原始行分别分析，再去重合并
    merged_reqs = [reader.merge_group(g) for g in groups]
    version_plans = VersionManager().get_version_plans(version_id)
    analyzer = RiskAnalyzer(version_plans)

    # 对每个原始行单独分析风险
    for raw_row in raw_rows:
        raw_row['risks'] = analyzer.analyze_requirement(raw_row)

    # 对每个组内的风险去重合并，并同步最小进度
    for idx, merged_req in enumerate(merged_reqs):
        group_rows = [r for r in raw_rows if r['_group_idx'] == idx]
        # 合并所有风险并去重
        all_risks = set()
        for r in group_rows:
            all_risks.update(r.get('risks', []))
        # 同步去重后的风险和最小进度到所有行
        min_progress = merged_req.get('测试进度', 0)
        for r in group_rows:
            r['risks'] = sorted(list(all_risks))
            r['测试进度'] = min_progress

    # 计算统计
    stats_calc = StatsCalculator(merged_reqs)
    stats = stats_calc.calculate_with_groups(groups)

    return jsonify({
        'success': True,
        'data': {
            'requirements': raw_rows,  # 原始所有行
            'groups': groups,          # 合并组信息
            'stats': stats
        }
    })


@app.route('/api/empty_fields', methods=['GET'])
def get_empty_fields():
    """获取空白字段统计"""
    version_id = request.args.get('version_id')
    if not version_id:
        return jsonify({'success': False, 'error': 'version_id required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        return jsonify({'success': False, 'error': 'No cache found'})

    reader = ExcelReader(cache_file)
    # 获取第一个sheet
    sheets = reader.get_sheet_names()
    if not sheets:
        return jsonify({'success': False, 'error': 'No sheets found'})

    reader.load_sheet(sheets[0])
    groups = reader.get_requirement_groups()
    merged_reqs = [reader.merge_group(g) for g in groups]

    # 计算空白字段统计
    stats_calc = StatsCalculator(merged_reqs)
    empty_stats = stats_calc.calculate_empty_fields_by_tester()

    return jsonify({
        'success': True,
        'data': {
            'empty_stats': empty_stats,
            'columns': EMPTY_FIELD_COLUMNS
        }
    })


# ============ 版本计划 API ============

@app.route('/api/version_plans', methods=['GET'])
def get_version_plans():
    """获取版本计划列表"""
    version_id = request.args.get('version_id')
    vm = VersionManager()
    plans = vm.get_version_plans(version_id)
    return jsonify({'success': True, 'data': {'plans': plans}})


@app.route('/api/version_plans', methods=['POST'])
def create_version_plan():
    """创建版本计划"""
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
    """更新版本计划"""
    data = request.json
    vm = VersionManager()
    success = vm.update_version_plan(plan_id, data.get('target_date'))
    return jsonify({'success': success})


@app.route('/api/version_plans/<int:plan_id>', methods=['DELETE'])
def delete_version_plan(plan_id):
    """删除版本计划"""
    vm = VersionManager()
    success = vm.delete_version_plan(plan_id)
    return jsonify({'success': success})


if __name__ == '__main__':
    app.run(debug=False, port=5001)
