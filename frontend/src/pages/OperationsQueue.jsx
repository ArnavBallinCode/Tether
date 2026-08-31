import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { ArrowUpDown } from 'lucide-react';

const OperationsQueue = () => {
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOpps = async () => {
      const data = await api.getOpportunities();
      setOpportunities(data);
      setLoading(false);
    };
    fetchOpps();
  }, []);

  const getStatusStyle = (status) => {
    switch (status) {
      case 'Recovered': return 'bg-green-100 text-green-700 border-green-200';
      case 'Escalated': return 'bg-red-100 text-red-700 border-red-200';
      case 'Open': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getRiskStyle = (level) => {
    switch (level) {
      case 'High': return 'text-red-600 font-semibold';
      case 'Medium': return 'text-yellow-600 font-semibold';
      case 'Low': return 'text-green-600 font-semibold';
      default: return 'text-gray-600';
    }
  };

  if (loading) return <div className="p-10">Loading...</div>;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900">Operations Queue</h2>
        <p className="text-gray-500 mt-1">Manage and track recovery opportunities</p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 font-medium">
              <tr>
                <th className="px-6 py-4">Customer</th>
                <th className="px-6 py-4">
                  <div className="flex items-center gap-1 cursor-pointer hover:text-gray-900">
                    Amount at Risk <ArrowUpDown className="w-4 h-4" />
                  </div>
                </th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Risk Level</th>
                <th className="px-6 py-4">PRS Score</th>
                <th className="px-6 py-4">AI Diagnosis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {opportunities.map((opp) => (
                <tr key={opp.id} className="hover:bg-gray-50 transition-colors cursor-pointer">
                  <td className="px-6 py-4 font-medium text-gray-900">{opp.customer_name}</td>
                  <td className="px-6 py-4 font-semibold text-gray-900">${opp.amount_at_risk.toLocaleString()}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs border ${getStatusStyle(opp.status)}`}>
                      {opp.status}
                    </span>
                  </td>
                  <td className={`px-6 py-4 ${getRiskStyle(opp.risk_level)}`}>{opp.risk_level}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${opp.prs_score > 80 ? 'bg-green-500' : opp.prs_score > 50 ? 'bg-yellow-500' : 'bg-red-500'}`} 
                          style={{width: `${opp.prs_score}%`}}
                        />
                      </div>
                      <span className="text-gray-600 text-xs">{opp.prs_score}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-600">{opp.likely_cause}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default OperationsQueue;
