import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { api } from '../api';
import { Trophy, TrendingUp, Activity } from 'lucide-react';

const EvaluationDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEval = async () => {
      const res = await api.getEvalThreeArm();
      setData(res.arms);
      setLoading(false);
    };
    fetchEval();
  }, []);

  if (loading) return <div className="p-10">Loading...</div>;

  return (
    <div className="p-8 space-y-8">
      <div className="mb-4">
        <h2 className="text-3xl font-bold text-gray-900">Evaluation Dashboard</h2>
        <p className="text-gray-500 mt-1">A/B/C Test Results: No Intervention vs Naive vs Tether AI</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-2xl p-6 text-white shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-indigo-100">Winner: Tether Agent</h3>
            <Trophy className="w-6 h-6 text-yellow-400" />
          </div>
          <div className="text-4xl font-bold mb-1">
            ${(data[2]?.net_recovery / 1000).toFixed(0)}k
          </div>
          <div className="text-sm text-indigo-200">Net Recovery</div>
        </div>
        
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-500">Incremental Lift</h3>
            <TrendingUp className="w-6 h-6 text-green-500" />
          </div>
          <div className="text-4xl font-bold text-gray-900 mb-1">
            +{(data[2]?.incremental_vs_no_intervention / 1000).toFixed(0)}k
          </div>
          <div className="text-sm text-gray-500">vs Baseline</div>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-500">Cost Efficiency</h3>
            <Activity className="w-6 h-6 text-blue-500" />
          </div>
          <div className="text-4xl font-bold text-gray-900 mb-1">
            {((data[2]?.net_recovery / (data[2]?.cost || 1))).toFixed(1)}x
          </div>
          <div className="text-sm text-gray-500">ROI Multiple</div>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 h-[400px]">
        <h3 className="text-lg font-bold text-gray-900 mb-6">Financial Impact by Arm</h3>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis dataKey="arm" axisLine={false} tickLine={false} tick={{fill: '#6B7280'}} />
            <YAxis axisLine={false} tickLine={false} tick={{fill: '#6B7280'}} tickFormatter={(v) => `$${v/1000}k`} />
            <Tooltip 
              cursor={{fill: '#F3F4F6'}}
              contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            />
            <Legend />
            <Bar dataKey="total_recovered" name="Total Recovered" fill="#4F46E5" radius={[4, 4, 0, 0]} />
            <Bar dataKey="net_recovery" name="Net Recovery" fill="#10B981" radius={[4, 4, 0, 0]} />
            <Bar dataKey="cost" name="Cost" fill="#EF4444" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 font-medium">
            <tr>
              <th className="px-6 py-4">Experimental Arm</th>
              <th className="px-6 py-4">Total Recovered</th>
              <th className="px-6 py-4">Cost</th>
              <th className="px-6 py-4">Net Recovery</th>
              <th className="px-6 py-4">Incremental (vs Baseline)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.map((arm, idx) => (
              <tr key={idx} className={idx === 2 ? 'bg-indigo-50/30' : ''}>
                <td className="px-6 py-4 font-medium text-gray-900">{arm.arm}</td>
                <td className="px-6 py-4">${arm.total_recovered.toLocaleString()}</td>
                <td className="px-6 py-4 text-red-600">
                  {arm.cost > 0 ? `-$${arm.cost.toLocaleString()}` : '$0'}
                </td>
                <td className="px-6 py-4 font-bold text-gray-900">${arm.net_recovery.toLocaleString()}</td>
                <td className="px-6 py-4 text-green-600 font-medium">
                  {arm.incremental_vs_no_intervention > 0 ? `+$${arm.incremental_vs_no_intervention.toLocaleString()}` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default EvaluationDashboard;
