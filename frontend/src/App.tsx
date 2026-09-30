import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { getAuthToken, apiRequest } from './api/client';
import { Dataset } from './types';

import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Upload } from './pages/Upload';
import { Profile } from './pages/Profile';
import { Rules } from './pages/Rules';
import { PlanAndLoss } from './pages/PlanAndLoss';
import { ApplyAndRollback } from './pages/ApplyAndRollback';
import { Verify } from './pages/Verify';
import { AdversarialLab } from './pages/AdversarialLab';
import { Benchmarks } from './pages/Benchmarks';
import { AuditAndHealth } from './pages/AuditAndHealth';

const ProtectedLayout: React.FC<{
  children: React.ReactNode;
  selectedDataset: Dataset | null;
  datasets: Dataset[];
  onSelectDataset: (d: Dataset) => void;
  onLoadDemo: () => void;
  isLoadingDemo: boolean;
}> = ({
  children,
  selectedDataset,
  datasets,
  onSelectDataset,
  onLoadDemo,
  isLoadingDemo,
}) => {
  const location = useLocation();
  const token = getAuthToken();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  const getPageTitle = (pathname: string): string => {
    switch (pathname) {
      case '/':
        return 'Enterprise Dashboard';
      case '/upload':
        return 'Dataset Ingestion & Upload Guard';
      case '/profile':
        return 'Deterministic Chunked Profiler';
      case '/rules':
        return 'Semantic Constraint Inference';
      case '/plan':
        return 'Plan & Information Loss Model';
      case '/apply':
        return 'Reversible Execution Ledger';
      case '/verify':
        return 'Pandera & Mutation Verification';
      case '/adversarial':
        return 'Adversarial Resilience Lab';
      case '/benchmarks':
        return 'Benchmarks & Scaling Evaluation';
      case '/audit':
        return 'Audit Logs & System Health';
      default:
        return 'CleanSlate';
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Sidebar currentDatasetId={selectedDataset?.id} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          title={getPageTitle(location.pathname)}
          datasets={datasets}
          selectedDataset={selectedDataset}
          onSelectDataset={onSelectDataset}
          onLoadDemo={onLoadDemo}
          isLoadingDemo={isLoadingDemo}
        />
        <main className="flex-1 overflow-y-auto p-8">{children}</main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [loadingDemo, setLoadingDemo] = useState(false);

  const fetchDatasets = async () => {
    try {
      const data = await apiRequest<Dataset[]>('/api/datasets');
      setDatasets(data);
      if (data.length > 0 && !selectedDataset) {
        setSelectedDataset(data[0]);
      }
    } catch {
      // Ignored if unauthenticated
    }
  };

  useEffect(() => {
    if (getAuthToken()) {
      fetchDatasets();
    }
  }, []);

  const handleLoadDemo = async () => {
    try {
      setLoadingDemo(true);
      const res = await apiRequest<{ dataset: Dataset }>('/api/datasets/demo', { method: 'POST' });
      setSelectedDataset(res.dataset);
      await fetchDatasets();
    } catch (err) {
      console.error('Failed to load demo:', err);
    } finally {
      setLoadingDemo(false);
    }
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedLayout
              selectedDataset={selectedDataset}
              datasets={datasets}
              onSelectDataset={setSelectedDataset}
              onLoadDemo={handleLoadDemo}
              isLoadingDemo={loadingDemo}
            >
              <Routes>
                <Route
                  path="/"
                  element={
                    <Dashboard
                      selectedDataset={selectedDataset}
                      onSelectDataset={setSelectedDataset}
                    />
                  }
                />
                <Route
                  path="/upload"
                  element={
                    <Upload
                      onDatasetLoaded={(d) => {
                        setSelectedDataset(d);
                        setDatasets((prev) => [d, ...prev.filter((x) => x.id !== d.id)]);
                      }}
                    />
                  }
                />
                <Route path="/profile" element={<Profile selectedDataset={selectedDataset} />} />
                <Route path="/rules" element={<Rules selectedDataset={selectedDataset} />} />
                <Route path="/plan" element={<PlanAndLoss selectedDataset={selectedDataset} />} />
                <Route
                  path="/apply"
                  element={<ApplyAndRollback selectedDataset={selectedDataset} />}
                />
                <Route path="/verify" element={<Verify selectedDataset={selectedDataset} />} />
                <Route path="/adversarial" element={<AdversarialLab />} />
                <Route path="/benchmarks" element={<Benchmarks />} />
                <Route path="/audit" element={<AuditAndHealth />} />
              </Routes>
            </ProtectedLayout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
};
