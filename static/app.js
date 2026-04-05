let currentVersion = null;
let currentSheet = null;
let allRequirements = [];
let allGroups = [];
let allStats = {};
let versionPlans = [];

async function init() {
    await loadVersions();
    setupEventListeners();
}

async function loadVersions() {
    try {
        const response = await fetch('/api/versions');
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('version-select');
            data.data.versions.forEach(v => {
                const option = document.createElement('option');
                option.value = v.version_id;
                option.textContent = v.name || v.version_id;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load versions:', error);
    }
}

function setupEventListeners() {
    document.getElementById('version-select').addEventListener('change', onVersionChange);
    document.getElementById('refresh-btn').addEventListener('click', refreshData);
    document.getElementById('add-plan-btn').addEventListener('click', showAddPlanModal);
    document.getElementById('cancel-plan-btn').addEventListener('click', hidePlanModal);
    document.getElementById('plan-form').addEventListener('submit', saveVersionPlan);
    document.getElementById('tester-filter').addEventListener('change', filterRequirements);
    document.getElementById('search-box').addEventListener('input', filterRequirements);

    // Risk card click handlers
    document.querySelectorAll('.risk-cards .card').forEach(card => {
        card.addEventListener('click', () => {
            const type = card.dataset.type;
            filterByRiskType(type);
        });
    });
}

async function onVersionChange(e) {
    currentVersion = e.target.value;

    if (!currentVersion) {
        clearDisplay();
        return;
    }

    // Load version plans
    await loadVersionPlans();

    // Get sheets
    try {
        const response = await fetch(`/api/sheets?version_id=${currentVersion}`);
        const data = await response.json();

        if (data.success) {
            // Find default sheet (with "需求列表" in name)
            currentSheet = data.data.sheets.find(s => s.includes('需求列表')) || data.data.sheets[0];
            await loadData();
        } else {
            alert(data.error || '加载失败');
        }
    } catch (error) {
        console.error('Failed to load sheets:', error);
        alert('加载失败');
    }
}

async function loadVersionPlans() {
    try {
        const response = await fetch(`/api/version_plans?version_id=${currentVersion}`);
        const data = await response.json();

        if (data.success) {
            versionPlans = data.data.plans || [];
            renderTimeline();
        }
    } catch (error) {
        console.error('Failed to load version plans:', error);
    }
}

function renderTimeline() {
    const container = document.getElementById('timeline-content');

    if (!versionPlans || versionPlans.length === 0) {
        container.innerHTML = '<p class="no-data">暂无版本计划</p>';
        return;
    }

    // Group by version_name
    const byVersion = {};
    versionPlans.forEach(p => {
        if (!byVersion[p.version_name]) {
            byVersion[p.version_name] = [];
        }
        byVersion[p.version_name].push(p);
    });

    let html = '';
    for (const [versionName, plans] of Object.entries(byVersion)) {
        html += `<div class="timeline-version">`;
        html += `<h4>${versionName}</h4>`;
        html += `<div class="timeline-stages">`;

        plans.sort((a, b) => a.id - b.id).forEach(plan => {
            const isOverdue = plan.target_date && new Date(plan.target_date) < new Date();
            html += `
                <div class="stage ${isOverdue ? 'overdue' : ''}">
                    <span class="stage-name">${plan.stage_name}</span>
                    <span class="stage-date">${plan.target_date || '未设置'}</span>
                </div>
            `;
        });

        html += `</div></div>`;
    }

    container.innerHTML = html;
}

async function loadData() {
    if (!currentVersion || !currentSheet) return;

    try {
        const response = await fetch('/api/load_sheet', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                version_id: currentVersion,
                sheet_name: currentSheet
            })
        });

        const data = await response.json();

        if (data.success) {
            allRequirements = data.data.requirements;
            allGroups = data.data.groups;
            allStats = data.data.stats || {};

            renderStats();
            renderRiskCards();
            populateTesterFilter();
            renderTable(allRequirements);
        } else {
            alert(data.error || '加载数据失败');
        }
    } catch (error) {
        console.error('Failed to load data:', error);
        alert('加载数据失败');
    }
}

function renderStats() {
    document.getElementById('stat-actual-count').textContent = allStats.actual_requirement_count || 0;
    document.getElementById('stat-total-count').textContent = allStats.total_row_count || 0;
    document.getElementById('stat-completed').textContent = allStats.completed_count || 0;
    document.getElementById('stat-in-progress').textContent = allStats.in_progress_count || 0;
    document.getElementById('stat-not-started').textContent = allStats.not_started_count || 0;
}

function renderRiskCards() {
    const risks = {
        not_started: allRequirements.filter(r =>
            r.risks && (r.risks.includes('serial_review_incomplete') || r.risks.includes('reverse_serial_incomplete'))
        ),
        delayed: allRequirements.filter(r =>
            r.risks && r.risks.includes('test_progress_delayed')
        ),
        empty_fields: allRequirements.filter(r =>
            r.risks && r.risks.some(risk => risk.startsWith('empty_field_'))
        )
    };

    document.querySelector('#card-not-started .count').textContent = risks.not_started.length;
    document.querySelector('#card-delayed .count').textContent = risks.delayed.length;
    document.querySelector('#card-empty .count').textContent = risks.empty_fields.length;
}

function populateTesterFilter() {
    const testers = [...new Set(allRequirements.map(r => r['测试人员']).filter(Boolean))];
    const select = document.getElementById('tester-filter');

    // Keep first option
    select.innerHTML = '<option value="">全部测试人员</option>';

    testers.forEach(tester => {
        const option = document.createElement('option');
        option.value = tester;
        option.textContent = tester;
        select.appendChild(option);
    });
}

function filterRequirements() {
    const tester = document.getElementById('tester-filter').value;
    const search = document.getElementById('search-box').value.toLowerCase();

    let filtered = allRequirements;

    if (tester) {
        filtered = filtered.filter(r => r['测试人员'] === tester);
    }

    if (search) {
        filtered = filtered.filter(r => {
            const id = (r['需求编号'] || '').toLowerCase();
            const desc = (r['需求描述'] || '').toLowerCase();
            return id.includes(search) || desc.includes(search);
        });
    }

    renderTable(filtered);
}

function filterByRiskType(type) {
    // Filter table to show only requirements with specific risk type
    const tester = document.getElementById('tester-filter').value;
    const search = document.getElementById('search-box').value.toLowerCase();

    let filtered = allRequirements;

    if (type === 'not-started') {
        filtered = filtered.filter(r =>
            r.risks && (r.risks.includes('serial_review_incomplete') || r.risks.includes('reverse_serial_incomplete'))
        );
    } else if (type === 'delayed') {
        filtered = filtered.filter(r =>
            r.risks && r.risks.includes('test_progress_delayed')
        );
    } else if (type === 'empty-fields') {
        filtered = filtered.filter(r =>
            r.risks && r.risks.some(risk => risk.startsWith('empty_field_'))
        );
    }

    if (tester) {
        filtered = filtered.filter(r => r['测试人员'] === tester);
    }

    if (search) {
        filtered = filtered.filter(r => {
            const id = (r['需求编号'] || '').toLowerCase();
            const desc = (r['需求描述'] || '').toLowerCase();
            return id.includes(search) || desc.includes(search);
        });
    }

    renderTable(filtered);
}

function renderTable(requirements) {
    const tbody = document.getElementById('requirements-body');

    if (!requirements || requirements.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="no-data">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = requirements.map(req => {
        const riskTags = (req.risks || []).map(risk =>
            `<span class="risk-tag ${risk}">${formatRiskLabel(risk)}</span>`
        ).join('');

        const detailLink = req['需求编号']
            ? `<a href="https://clouddevops.huawei.com/workitem/+${req['需求编号']}" target="_blank">详情</a>`
            : '';

        const progress = req['测试进度'] || 0;
        const progressClass = progress >= 100 ? 'progress-complete' : progress > 0 ? 'progress-active' : 'progress-zero';

        return `
            <tr>
                <td>${req['需求编号'] || ''}</td>
                <td>${req['特性分类'] || ''}</td>
                <td>${req['测试人员'] || ''}</td>
                <td class="${progressClass}">${progress}%</td>
                <td>${riskTags}</td>
                <td>${detailLink}</td>
            </tr>
        `;
    }).join('');
}

function formatRiskLabel(risk) {
    const labels = {
        'serial_review_incomplete': '串讲未完成',
        'reverse_serial_incomplete': '反串讲未完成',
        'test_progress_delayed': '进度滞后',
        'empty_field_测试人员': '测试人员空白',
        'empty_field_计划转测时间': '计划转测时间空白',
        'empty_field_测试进度': '测试进度空白'
    };
    return labels[risk] || risk;
}

async function refreshData() {
    if (!currentVersion) return;
    await loadData();
}

function showAddPlanModal() {
    if (!currentVersion) {
        alert('请先选择版本');
        return;
    }

    document.getElementById('plan-version-id').value = currentVersion;
    document.getElementById('plan-modal').classList.add('show');
}

function hidePlanModal() {
    document.getElementById('plan-modal').classList.remove('show');
    document.getElementById('plan-form').reset();
}

async function saveVersionPlan(e) {
    e.preventDefault();

    const version_id = document.getElementById('plan-version-id').value;
    const stage_name = document.getElementById('plan-stage-name').value;
    const target_date = document.getElementById('plan-target-date').value;

    try {
        const response = await fetch('/api/version_plans', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                version_id: version_id,
                version_name: 'Beta_T1',  // Default version name
                stage_name: stage_name,
                target_date: target_date
            })
        });

        const data = await response.json();

        if (data.success) {
            hidePlanModal();
            await loadVersionPlans();
            await loadData();  // Recalculate risks with new plans
        } else {
            alert('保存失败');
        }
    } catch (error) {
        console.error('Failed to save plan:', error);
        alert('保存失败');
    }
}

function clearDisplay() {
    allRequirements = [];
    allGroups = [];
    allStats = {};
    versionPlans = [];

    document.getElementById('stat-actual-count').textContent = '-';
    document.getElementById('stat-total-count').textContent = '-';
    document.getElementById('stat-completed').textContent = '-';
    document.getElementById('stat-in-progress').textContent = '-';
    document.getElementById('stat-not-started').textContent = '-';

    document.querySelector('#card-not-started .count').textContent = '0';
    document.querySelector('#card-delayed .count').textContent = '0';
    document.querySelector('#card-empty .count').textContent = '0';

    document.getElementById('timeline-content').innerHTML = '';
    document.getElementById('requirements-body').innerHTML = '';

    // Reset tester filter
    document.getElementById('tester-filter').innerHTML = '<option value="">全部测试人员</option>';
}

// Initialize on load
document.addEventListener('DOMContentLoaded', init);