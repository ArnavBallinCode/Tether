// API Integration Service

export const api = {
  async getDashboardMetrics() {
    try {
      const res = await fetch('/api/dashboard_metrics');
      if (!res.ok) throw new Error('Network response was not ok');
      return await res.json();
    } catch (e) {
      console.error(e);
      // Mock fallback
      return {
        revenue_at_risk: 1500000,
        money_recovered: 850000,
        total_cases: 120,
        automation_rate: 75,
        status_breakdown: [
          { name: 'Recovered', value: 75 },
          { name: 'Open', value: 20 },
          { name: 'Escalated', value: 15 },
          { name: 'Failed', value: 10 },
        ],
        escalated_count: 15,
      };
    }
  },

  async getOpportunities() {
    try {
      const res = await fetch('/api/opportunities');
      if (!res.ok) throw new Error('Network response was not ok');
      return await res.json();
    } catch (e) {
      console.error(e);
      // Mock fallback
      return [
        { id: 1, customer_name: 'Acme Corp', amount_at_risk: 50000, status: 'Recovered', risk_level: 'Low', likely_cause: 'Expired Card', prs_score: 95, recovered_amount: 50000 },
        { id: 2, customer_name: 'Stark Ind', amount_at_risk: 120000, status: 'Escalated', risk_level: 'High', likely_cause: 'Dispute', prs_score: 40, recovered_amount: 0 },
        { id: 3, customer_name: 'Wayne Ent', amount_at_risk: 75000, status: 'Open', risk_level: 'Medium', likely_cause: 'Insufficient Funds', prs_score: 75, recovered_amount: 0 },
      ];
    }
  },

  async getAuditLogs() {
    try {
      const res = await fetch('/api/audit_logs');
      if (!res.ok) throw new Error('Network response was not ok');
      return await res.json();
    } catch (e) {
      console.error(e);
      // Mock fallback
      return [
        { opportunity_id: 1, action: 'Detected anomaly', details: 'Payment failed due to expired card', timestamp: new Date(Date.now() - 3600000).toISOString(), passed_guardrails: true, guardrail_notes: 'Standard retry flow', phase: 'Detect' },
        { opportunity_id: 1, action: 'Automated email sent', details: 'Sent updated card link to billing contact', timestamp: new Date(Date.now() - 3000000).toISOString(), passed_guardrails: true, guardrail_notes: 'Within email limits', phase: 'Act' },
      ];
    }
  },

  async getPipelineStatus() {
    try {
      const res = await fetch('/api/pipeline_status');
      if (!res.ok) throw new Error('Network response was not ok');
      return await res.json();
    } catch (e) {
      console.error(e);
      // Mock fallback
      return {
        stages: [
          { name: 'Detect', count: 120, active: true },
          { name: 'Diagnose', count: 115, active: true },
          { name: 'Decide', count: 90, active: true },
          { name: 'Policy Gate', count: 85, active: true },
          { name: 'Execute', count: 80, active: true },
          { name: 'Verify', count: 75, active: false },
        ]
      };
    }
  },

  async getEvalThreeArm() {
    try {
      const res = await fetch('/api/eval/three_arm');
      if (!res.ok) throw new Error('Network response was not ok');
      return await res.json();
    } catch (e) {
      console.error(e);
      // Mock fallback
      return {
        arms: [
          { arm: 'No Intervention', total_recovered: 200000, cost: 0, net_recovery: 200000, incremental_vs_no_intervention: 0 },
          { arm: 'Naive Uniform', total_recovered: 450000, cost: 50000, net_recovery: 400000, incremental_vs_no_intervention: 200000 },
          { arm: 'Tether Agent', total_recovered: 900000, cost: 20000, net_recovery: 880000, incremental_vs_no_intervention: 680000 },
        ]
      };
    }
  },

  async runRecovery() {
    try {
      const res = await fetch('/api/run_recovery', { method: 'POST' });
      return await res.json();
    } catch (e) {
      console.error(e);
      return { status: "started" };
    }
  },

  async reset() {
    try {
      const res = await fetch('/api/reset', { method: 'POST' });
      return await res.json();
    } catch (e) {
      console.error(e);
      return { status: "success" };
    }
  }
};
