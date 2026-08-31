import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../api';
import { Search, Stethoscope, BrainCircuit, ShieldCheck, Zap, CheckCircle2 } from 'lucide-react';

const icons = {
  'Detect': Search,
  'Diagnose': Stethoscope,
  'Decide': BrainCircuit,
  'Policy Gate': ShieldCheck,
  'Execute': Zap,
  'Verify': CheckCircle2,
};

const PipelineFlow = () => {
  const [stages, setStages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      const data = await api.getPipelineStatus();
      setStages(data.stages || []);
      setLoading(false);
    };
    
    fetchStatus();
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex-1 h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="p-10 h-full flex flex-col relative overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-50 via-gray-50 to-white">
      <div className="mb-12">
        <h2 className="text-4xl font-extrabold text-gray-900 tracking-tight">Recovery Pipeline</h2>
        <p className="text-gray-500 mt-2 text-lg">Real-time autonomous revenue recovery process flow</p>
      </div>

      <div className="flex-1 flex items-center justify-center w-full max-w-6xl mx-auto relative">
        {/* Connection line background */}
        <div className="absolute top-1/2 left-10 right-10 h-1 bg-gray-200 -translate-y-1/2 rounded-full z-0"></div>
        
        <div className="flex justify-between w-full relative z-10">
          {stages.map((stage, idx) => {
            const Icon = icons[stage.name] || Search;
            const isActive = stage.active;
            const hasItems = stage.count > 0;
            
            return (
              <div key={stage.name} className="flex flex-col items-center relative group w-32">
                {/* Connecting animated line */}
                {idx > 0 && (
                  <div className="absolute top-10 right-1/2 w-full h-1 -translate-y-1/2 -z-10">
                    <motion.div 
                      className={`h-full ${isActive ? 'bg-indigo-500' : 'bg-gray-200'}`}
                      initial={{ width: 0 }}
                      animate={{ width: '100%' }}
                      transition={{ duration: 1, delay: idx * 0.2 }}
                    />
                  </div>
                )}
                
                {/* Stage Node */}
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.5, delay: idx * 0.1 }}
                  className={`
                    w-20 h-20 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-300
                    ${isActive ? 'bg-indigo-600 text-white shadow-indigo-500/40 ring-4 ring-indigo-200' : 
                      hasItems ? 'bg-white text-gray-800 border-2 border-gray-200' : 'bg-gray-100 text-gray-400'}
                  `}
                >
                  <Icon className={`w-8 h-8 ${isActive ? 'animate-pulse' : ''}`} />
                  
                  {/* Floating particle effect when active */}
                  <AnimatePresence>
                    {isActive && hasItems && (
                      <motion.div
                        className="absolute inset-0 rounded-2xl border-2 border-indigo-400"
                        initial={{ scale: 1, opacity: 1 }}
                        animate={{ scale: 1.5, opacity: 0 }}
                        transition={{ repeat: Infinity, duration: 1.5 }}
                      />
                    )}
                  </AnimatePresence>
                </motion.div>

                {/* Stage Label & Count */}
                <div className="mt-6 text-center">
                  <h3 className={`font-bold text-sm uppercase tracking-wider ${isActive ? 'text-indigo-600' : 'text-gray-600'}`}>
                    {stage.name}
                  </h3>
                  <motion.div 
                    key={stage.count}
                    initial={{ y: -10, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    className={`
                      inline-flex items-center justify-center px-3 py-1 mt-2 rounded-full text-sm font-semibold
                      ${isActive ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'}
                    `}
                  >
                    {stage.count} cases
                  </motion.div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default PipelineFlow;
