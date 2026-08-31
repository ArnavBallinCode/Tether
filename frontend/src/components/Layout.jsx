import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Activity, LayoutDashboard, List, History, BarChart2, Play, RefreshCw } from 'lucide-react';
import { api } from '../api';

const Layout = () => {
  const [isRunning, setIsRunning] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await api.getPipelineStatus();
        setIsRunning(data.is_running);
      } catch (e) {}
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleRunRecovery = async () => {
    setIsRunning(true);
    await api.runRecovery();
  };

  const handleReset = async () => {
    await api.reset();
  };

  const navItems = [
    { name: 'Pipeline Flow', path: '/', icon: Activity },
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Operations', path: '/operations', icon: List },
    { name: 'Audit Trail', path: '/audit', icon: History },
    { name: 'Evaluation', path: '/evaluation', icon: BarChart2 },
  ];

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col shadow-xl z-10">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-indigo-400 flex items-center gap-2">
            <Activity className="w-6 h-6 text-indigo-500" />
            Tether AI
          </h1>
          <p className="text-xs text-gray-400 mt-1">Revenue Recovery Platform</p>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </NavLink>
          ))}
        </nav>
        
        <div className="p-4 space-y-3 mb-4">
          <button
            onClick={handleRunRecovery}
            disabled={isRunning}
            className={`w-full flex items-center justify-center gap-2 py-3 rounded-lg font-semibold transition-all shadow-lg ${
              isRunning ? 'bg-indigo-800 text-indigo-300 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 text-white hover:shadow-indigo-500/25'
            }`}
          >
            {isRunning ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <Play className="w-5 h-5" />
            )}
            {isRunning ? 'Running...' : 'Run Recovery'}
          </button>
          
          <button
            onClick={handleReset}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors border border-gray-700 hover:border-gray-600"
          >
            <RefreshCw className="w-4 h-4" />
            Reset Data
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-gray-50 relative">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
