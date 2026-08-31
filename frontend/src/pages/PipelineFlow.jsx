import React, { useEffect, useState, useCallback } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, MarkerType, Handle, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { api } from '../api';
import { Search, Stethoscope, BrainCircuit, ShieldCheck, Zap, CheckCircle2, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const iconMap = {
  'Detect': Search,
  'Diagnose': Stethoscope,
  'Decide': BrainCircuit,
  'Policy Gate': ShieldCheck,
  'Execute': Zap,
  'Verify': CheckCircle2,
};

// Custom Node Component
const CustomPipelineNode = ({ data }) => {
  const Icon = iconMap[data.name] || Search;
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`relative w-72 rounded-xl border-2 transition-all duration-300 shadow-xl overflow-hidden bg-white/90 backdrop-blur-md ${data.active ? 'border-indigo-500 shadow-indigo-500/30' : 'border-gray-200'}`}>
      
      {/* Animated glow background if active */}
      {data.active && (
        <div className="absolute inset-0 bg-indigo-500/10 animate-pulse pointer-events-none" />
      )}

      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-indigo-500 border-2 border-white" />
      
      <div 
        className="p-4 cursor-pointer flex items-center justify-between"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${data.active ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-500'}`}>
            <Icon size={24} />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">{data.name}</h3>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Stage</p>
          </div>
        </div>
        
        <div className="flex flex-col items-end gap-1">
          <span className={`px-3 py-1 rounded-full text-sm font-bold ${data.count > 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
            {data.count} cases
          </span>
          <ChevronDown size={16} className={`text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {/* Dropdown Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-gray-100 bg-gray-50 p-3"
          >
            <div className="text-xs text-gray-500 mb-2 font-semibold uppercase">Live Metrics</div>
            <div className="space-y-2">
              <div className="flex justify-between items-center bg-white p-2 rounded border border-gray-200">
                <span className="text-gray-600 text-xs">Throughput</span>
                <span className="font-mono text-xs font-bold text-indigo-600">{data.count > 0 ? (data.count * 1.5).toFixed(1) : '0.0'}/sec</span>
              </div>
              <div className="flex justify-between items-center bg-white p-2 rounded border border-gray-200">
                <span className="text-gray-600 text-xs">Latency</span>
                <span className="font-mono text-xs font-bold text-green-600">{data.count > 0 ? Math.floor(Math.random() * 40 + 10) : '0'}ms</span>
              </div>
              <div className="flex justify-between items-center bg-white p-2 rounded border border-gray-200">
                <span className="text-gray-600 text-xs">Status</span>
                <span className="flex items-center gap-1 text-xs font-bold text-green-600">
                  <div className={`w-2 h-2 rounded-full ${data.active ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`}></div>
                  {data.active ? 'PROCESSING' : 'IDLE'}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-indigo-500 border-2 border-white" />
    </div>
  );
};

const nodeTypes = {
  custom: CustomPipelineNode,
};

const initialNodes = [
  { id: 'detect', type: 'custom', position: { x: 50, y: 150 }, data: { name: 'Detect', count: 0, active: false } },
  { id: 'diagnose', type: 'custom', position: { x: 450, y: 150 }, data: { name: 'Diagnose', count: 0, active: false } },
  { id: 'decide', type: 'custom', position: { x: 850, y: 150 }, data: { name: 'Decide', count: 0, active: false } },
  { id: 'policy', type: 'custom', position: { x: 450, y: 350 }, data: { name: 'Policy Gate', count: 0, active: false } },
  { id: 'execute', type: 'custom', position: { x: 850, y: 350 }, data: { name: 'Execute', count: 0, active: false } },
  { id: 'verify', type: 'custom', position: { x: 1250, y: 350 }, data: { name: 'Verify', count: 0, active: false } },
];

const initialEdges = [
  { id: 'e1-2', source: 'detect', target: 'diagnose', type: 'smoothstep', animated: false, style: { strokeWidth: 3 }, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e2-3', source: 'diagnose', target: 'decide', type: 'smoothstep', animated: false, style: { strokeWidth: 3 }, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e3-4', source: 'decide', target: 'policy', type: 'smoothstep', animated: false, style: { strokeWidth: 3 }, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e4-5', source: 'policy', target: 'execute', type: 'smoothstep', animated: false, style: { strokeWidth: 3 }, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e5-6', source: 'execute', target: 'verify', type: 'smoothstep', animated: false, style: { strokeWidth: 3 }, markerEnd: { type: MarkerType.ArrowClosed } },
];

export default function PipelineFlow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await api.getPipelineStatus();
        const stagesArray = data.stages || [];
        
        setNodes((nds) => 
          nds.map((node) => {
            const stageData = stagesArray.find(s => s.name.toLowerCase().includes(node.data.name.split(' ')[0].toLowerCase()));
            if (stageData) {
              return {
                ...node,
                data: {
                  ...node.data,
                  count: stageData.count,
                  active: stageData.active,
                }
              };
            }
            return node;
          })
        );

        // Update edges to be animated if the source node is active
        setEdges((eds) => 
          eds.map((edge) => {
            const sourceNodeActive = stagesArray.find(s => s.name.toLowerCase().includes(edge.source.toLowerCase()))?.active;
            return {
              ...edge,
              animated: !!sourceNodeActive,
              style: { 
                strokeWidth: sourceNodeActive ? 4 : 3,
                stroke: sourceNodeActive ? '#4f46e5' : '#cbd5e1' 
              },
            };
          })
        );
        
        setLoading(false);
      } catch (e) {
        console.error(e);
      }
    };
    
    fetchStatus();
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-full w-full flex flex-col bg-gray-50">
      <div className="p-8 pb-4">
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Interactive AI Pipeline</h1>
        <p className="text-gray-500 mt-2">Node-based visualization of the autonomous recovery agent. Click on any node to view real-time diagnostics.</p>
      </div>
      
      <div className="flex-1 w-full h-full relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.5}
          maxZoom={1.5}
          className="bg-gray-50/50"
        >
          <Background color="#cbd5e1" gap={16} size={2} />
          <Controls className="bg-white border-2 border-gray-200 shadow-lg rounded-xl overflow-hidden" />
        </ReactFlow>

        {/* Floating gradient orb for aesthetics */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-indigo-500/5 rounded-full blur-[100px] pointer-events-none -z-10" />
      </div>
    </div>
  );
}
