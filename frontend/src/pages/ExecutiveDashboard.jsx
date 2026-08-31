import React, { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { api } from '../api';
import { DollarSign, ShieldAlert, TrendingUp, Cpu } from 'lucide-react';
import { motion } from 'framer-motion';

const COLORS = ['#10B981', '#F59E0B', '#EF4444', '#6B7280']; // Green, Yellow, Red, Gray

const ExecutiveDashboard = () => {
  const [metrics, setMetrics] = useState(null);
  
  // Mock time series data for the area chart
  const areaData = [
    { time: '09:00', recovered: 100000 },
    { time: '10:00', recovered: 250000 },
    { time: '11:00', recovered: 400000 },
    { time: '12:00', recovered: 600000 },
    { time: '13:00', recovered: 850000 },
  ];

  useEffect(() => {
    const fetchMetrics = async () => {
      const data = await api.getDashboardMetrics();
      setMetrics(data);
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 2000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) return <div className="p-10">Loading...</div>;

  const StatCard = ({ title, value, prefix, suffix, icon: Icon, colorClass }) => (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100"
    >
      <div className="flex justify-between items-start">
        <div>
          <p className="text-gray-500 text-sm font-medium">{title}</p>
          <h3 className={`text-3xl font-bold mt-2 ${colorClass || 'text-gray-900'}`}>
            {prefix}{value.toLocaleString()}{suffix}
          </h3>
        </div>
        <div className={`p-3 rounded-xl ${colorClass ? colorClass.replace('text-', 'bg-').replace('600', '100') : 'bg-gray-100'}`}>
          <Icon className={`w-6 h-6 ${colorClass || 'text-gray-600'}`} />
        </div>
      </div>
    </motion.div>
  );

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Executive Dashboard</h2>
          <p className="text-gray-500 mt-1">Real-time recovery performance and risk metrics</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Revenue at Risk" 
          value={metrics.revenue_at_risk} 
          prefix="$" 
          icon={ShieldAlert}
          colorClass="text-red-600"
        />
        <StatCard 
          title="Money Recovered" 
          value={metrics.money_recovered.toLocaleString()} 
          prefix="$" 
          icon={TrendingUp}
          colorClass="text-indigo-600"
        />
        <StatCard 
          title="Automation Rate" 
          value={(metrics.automation_rate * 100).toFixed(1)} 
          suffix="%" 
          icon={Cpu} 
          trend="+5.2%" 
          color="text-green-600 bg-green-50"
        />
        <StatCard 
          title="Escalations" 
          value={metrics.escalated_count} 
          icon={DollarSign} 
          color="text-yellow-600 bg-yellow-50"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[400px]">
        {/* Area Chart */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 lg:col-span-2">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Cumulative Recovery Curve</h3>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={areaData}>
              <defs>
                <linearGradient id="colorRecovered" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#4F46E5" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
              <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{fill: '#6B7280'}} />
              <YAxis axisLine={false} tickLine={false} tick={{fill: '#6B7280'}} tickFormatter={(val) => `$${val/1000}k`} />
              <Tooltip 
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                formatter={(value) => [`$${value.toLocaleString()}`, 'Recovered']}
              />
              <Area type="monotone" dataKey="recovered" stroke="#4F46E5" strokeWidth={3} fillOpacity={1} fill="url(#colorRecovered)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pie Chart */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col">
          <h3 className="text-lg font-bold text-gray-900 mb-2">Status Distribution</h3>
          <div className="flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={metrics.status_breakdown}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {metrics.status_breakdown.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-4">
            {metrics.status_breakdown.map((item, idx) => (
              <div key={item.name} className="flex items-center gap-2 text-sm">
                <div className="w-3 h-3 rounded-full" style={{backgroundColor: COLORS[idx % COLORS.length]}}></div>
                <span className="text-gray-600">{item.name}:</span>
                <span className="font-semibold text-gray-900">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExecutiveDashboard;
