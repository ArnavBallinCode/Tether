import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import PipelineFlow from './pages/PipelineFlow';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import OperationsQueue from './pages/OperationsQueue';
import AuditTrail from './pages/AuditTrail';
import EvaluationDashboard from './pages/EvaluationDashboard';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<PipelineFlow />} />
        <Route path="dashboard" element={<ExecutiveDashboard />} />
        <Route path="operations" element={<OperationsQueue />} />
        <Route path="audit" element={<AuditTrail />} />
        <Route path="evaluation" element={<EvaluationDashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
