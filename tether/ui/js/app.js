const formatMoney = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
};

const getStatusBadge = (status) => {
    const map = {
        'open': '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">Open</span>',
        'recovered': '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">Recovered</span>',
        'failed': '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">Failed</span>',
        'escalated': '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">Escalated</span>'
    };
    return map[status] || status;
};

const getRiskBadge = (risk) => {
    if (!risk) return '-';
    const map = {
        'low': '<span class="text-green-600 font-medium">Low</span>',
        'medium': '<span class="text-yellow-600 font-medium">Medium</span>',
        'high': '<span class="text-orange-600 font-medium">High</span>',
        'critical': '<span class="text-red-600 font-medium font-bold">Critical</span>'
    };
    return map[risk] || risk;
};

async function updateDashboard() {
    try {
        const [metricsRes, oppsRes, logsRes] = await Promise.all([
            fetch('/api/dashboard_metrics'),
            fetch('/api/opportunities'),
            fetch('/api/audit_logs')
        ]);
        
        const metrics = await metricsRes.json();
        const opps = await oppsRes.json();
        const logs = await logsRes.json();

        // Update metrics
        document.getElementById('metricRisk').textContent = formatMoney(metrics.revenue_at_risk);
        document.getElementById('metricRecovered').textContent = formatMoney(metrics.money_recovered);
        document.getElementById('metricCases').textContent = metrics.total_cases;
        document.getElementById('metricAutomation').textContent = `${(metrics.automation_rate * 100).toFixed(1)}%`;
        document.getElementById('metricEscalated').textContent = metrics.status_breakdown.escalated || 0;

        // Update operations table
        const tbody = document.getElementById('opsTableBody');
        tbody.innerHTML = '';
        opps.forEach(opp => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${opp.customer_name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formatMoney(opp.amount_at_risk)}</td>
                <td class="px-6 py-4 whitespace-nowrap">${getStatusBadge(opp.status)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${getRiskBadge(opp.risk_level)}
                    ${opp.likely_cause ? `<span class="text-xs text-gray-400 block truncate w-32">${opp.likely_cause}</span>` : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Update audit log
        const logContainer = document.getElementById('auditLogContainer');
        logContainer.innerHTML = '';
        logs.forEach(log => {
            const div = document.createElement('div');
            div.className = 'border-l-2 border-indigo-200 pl-4 py-1';
            
            let detailsHtml = '';
            if (log.action === 'Diagnose') {
                detailsHtml = `Diagnosed as ${log.details.risk_level} risk. Cause: ${log.details.likely_cause}. PRS: ${log.details.prs_score}`;
            } else if (log.action === 'Plan (EIV)') {
                detailsHtml = `Selected action: ${log.details.action} (EIV: $${log.details.expected_incremental_value})<br/><span class="text-xs italic text-gray-400">Prob: ${(log.details.probability * 100).toFixed(0)}%</span>`;
            } else if (log.action === 'Policy Validation') {
                detailsHtml = log.passed_guardrails ? 
                    `<span class="text-green-600"><i class="fas fa-check-circle mr-1"></i> Guardrail passed</span>` : 
                    `<span class="text-red-600"><i class="fas fa-times-circle mr-1"></i> Blocked: ${log.guardrail_notes}</span>`;
            } else if (log.action === 'Execute') {
                const color = log.details.result === 'Success' ? 'text-green-600 font-semibold' : 'text-gray-600';
                detailsHtml = `Executed ${log.details.action}. Result: <span class="${color}">${log.details.result}</span>`;
            }

            div.innerHTML = `
                <div class="text-xs text-gray-400">${new Date(log.timestamp).toLocaleTimeString()}</div>
                <div class="text-sm font-medium text-gray-900">${log.action}</div>
                <div class="text-sm text-gray-600 mt-1">${detailsHtml}</div>
            `;
            logContainer.appendChild(div);
        });

        document.getElementById('lastUpdated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    } catch (e) {
        console.error("Error updating dashboard", e);
    }
}

document.getElementById('runRecoveryBtn').addEventListener('click', async () => {
    const btn = document.getElementById('runRecoveryBtn');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Running...';
    btn.disabled = true;
    
    await fetch('/api/run_recovery', { method: 'POST' });
    
    // Poll for updates
    const interval = setInterval(updateDashboard, 1000);
    setTimeout(() => {
        clearInterval(interval);
        btn.innerHTML = '<i class="fas fa-play mr-2"></i> Run Recovery';
        btn.disabled = false;
        updateDashboard();
    }, 5000);
});

document.getElementById('resetBtn').addEventListener('click', async () => {
    await fetch('/api/reset', { method: 'POST' });
    updateDashboard();
});

// Initial load
updateDashboard();

// Navigation Logic
const views = {
    dashboard: document.getElementById('viewDashboard'),
    operations: document.getElementById('viewOperations'),
    audit: document.getElementById('viewAudit')
};

const navs = {
    dashboard: document.getElementById('navDashboard'),
    operations: document.getElementById('navOperations'),
    audit: document.getElementById('navAudit')
};

function switchView(viewName) {
    // Hide all views
    Object.values(views).forEach(v => v.classList.add('hidden'));
    // Show selected view
    views[viewName].classList.remove('hidden');
    
    // Update nav styling
    Object.values(navs).forEach(n => {
        n.classList.remove('bg-gray-800', 'text-white');
        n.classList.add('text-gray-300');
    });
    navs[viewName].classList.remove('text-gray-300');
    navs[viewName].classList.add('bg-gray-800', 'text-white');
    
    document.getElementById('pageTitle').textContent = 
        viewName === 'dashboard' ? 'Executive Dashboard' : 
        viewName === 'operations' ? 'Operations Queue' : 'Live Audit Trail';
}

navs.dashboard.addEventListener('click', () => switchView('dashboard'));
navs.operations.addEventListener('click', () => switchView('operations'));
navs.audit.addEventListener('click', () => switchView('audit'));
