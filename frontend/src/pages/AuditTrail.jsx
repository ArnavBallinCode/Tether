import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { Clock, Shield, CheckCircle, AlertTriangle, FileText } from 'lucide-react';

const AuditTrail = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      const data = await api.getAuditLogs();
      setLogs(data);
      setLoading(false);
    };
    fetchLogs();
  }, []);

  const getPhaseColor = (phase) => {
    const colors = {
      'Detect': 'bg-blue-100 text-blue-700',
      'Diagnose': 'bg-purple-100 text-purple-700',
      'Decide': 'bg-indigo-100 text-indigo-700',
      'Act': 'bg-orange-100 text-orange-700',
      'Verify': 'bg-green-100 text-green-700',
    };
    return colors[phase] || 'bg-gray-100 text-gray-700';
  };

  if (loading) return <div className="p-10">Loading...</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900">Audit Trail</h2>
        <p className="text-gray-500 mt-1">Detailed immutable record of all AI actions and policy checks</p>
      </div>

      <div className="relative border-l-2 border-gray-200 ml-4 space-y-8">
        {logs.map((log, idx) => (
          <div key={idx} className="relative pl-8">
            {/* Timeline dot */}
            <div className={`absolute -left-2.5 top-2 w-5 h-5 rounded-full border-4 border-white ${
              log.passed_guardrails ? 'bg-indigo-500' : 'bg-red-500'
            }`}></div>

            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${getPhaseColor(log.phase)}`}>
                    {log.phase || 'System'}
                  </span>
                  <h3 className="text-lg font-bold text-gray-900">{log.action}</h3>
                </div>
                <div className="flex items-center text-gray-400 text-sm gap-1">
                  <Clock className="w-4 h-4" />
                  {new Date(log.timestamp).toLocaleTimeString()}
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 mt-3 border border-gray-100">
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-gray-500 mt-0.5" />
                  <p className="text-gray-700 text-sm leading-relaxed font-mono text-xs">{log.details}</p>
                </div>
              </div>
              
              {log.draft_message && (
                <div className="bg-indigo-50/50 rounded-lg p-4 mt-3 border border-indigo-100">
                  <div className="flex items-start gap-3">
                    <div className="bg-indigo-100 text-indigo-700 text-[10px] font-bold px-2 py-1 rounded uppercase tracking-widest shrink-0 mt-1">AI Draft</div>
                    <p className="text-indigo-900 text-sm italic leading-relaxed">"{log.draft_message}"</p>
                  </div>
                </div>
              )}

              <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-600">Policy Gate Check</span>
                </div>
                
                {log.passed_guardrails ? (
                  <div className="flex items-center gap-1.5 text-sm font-medium text-green-600 bg-green-50 px-3 py-1 rounded-full">
                    <CheckCircle className="w-4 h-4" /> Pass
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-sm font-medium text-red-600 bg-red-50 px-3 py-1 rounded-full">
                    <AlertTriangle className="w-4 h-4" /> Blocked
                  </div>
                )}
              </div>
              
              {log.guardrail_notes && (
                <p className="text-xs text-gray-500 mt-2 ml-1 text-right italic">
                  Rationale: {log.guardrail_notes}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AuditTrail;
