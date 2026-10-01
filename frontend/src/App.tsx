import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { motion, useSpring, useMotionValue } from 'framer-motion';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { getAuthToken, apiRequest } from './api/client';
import { Dataset } from './types';

import { LandingPage } from './pages/LandingPage';
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
}> = ({
  children,
  selectedDataset,
  datasets,
  onSelectDataset,
}) => {
  const location = useLocation();
  const token = getAuthToken();

  // Mouse tracking for dynamic cursor glow and ambient spotlight (same as Landing Page)
  const mouseX = useMotionValue(-100);
  const mouseY = useMotionValue(-100);
  const springConfig = { damping: 24, stiffness: 220, mass: 0.6 };
  const smoothX = useSpring(mouseX, springConfig);
  const smoothY = useSpring(mouseY, springConfig);
  const [rawMouse, setRawMouse] = useState({ x: -100, y: -100 });
  const [isHoveringInteractive, setIsHoveringInteractive] = useState(false);
  const [isMouseInWindow, setIsMouseInWindow] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setIsMouseInWindow(true);
      setRawMouse({ x: e.clientX, y: e.clientY });
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);

      const target = e.target as HTMLElement | null;
      if (target) {
        const interactive = target.closest('a, button, input, select, [role="button"], tr');
        setIsHoveringInteractive(!!interactive);
      }
    };

    const handleMouseLeave = () => setIsMouseInWindow(false);
    const handleMouseEnter = () => setIsMouseInWindow(true);

    window.addEventListener('mousemove', handleMouseMove);
    document.documentElement.addEventListener('mouseleave', handleMouseLeave);
    document.documentElement.addEventListener('mouseenter', handleMouseEnter);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.documentElement.removeEventListener('mouseleave', handleMouseLeave);
      document.documentElement.removeEventListener('mouseenter', handleMouseEnter);
    };
  }, [mouseX, mouseY]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  const getPageTitle = (pathname: string): string => {
    switch (pathname) {
      case '/dashboard':
        return 'Dashboard';
      case '/upload':
        return 'Ingestion & Upload';
      case '/profile':
        return 'Dataset Profiler';
      case '/rules':
        return 'Quality Rules';
      case '/plan':
        return 'Cleaning Plan';
      case '/apply':
        return 'Reversible Ledger';
      case '/verify':
        return 'Verification Suite';
      case '/adversarial':
        return 'Adversarial Lab';
      case '/benchmarks':
        return 'Benchmarks';
      case '/audit':
        return 'Audit & Health';
      default:
        return 'Workspace';
    }
  };

  return (
    <div className="relative flex h-screen w-full bg-black text-neutral-100 overflow-hidden font-sans selection:bg-neutral-800 selection:text-white">
      {/* Interactive Cursor Spotlight (same as Landing Page) */}
      {isMouseInWindow && (
        <motion.div
          className="pointer-events-none fixed top-0 left-0 z-50 rounded-full bg-radial from-emerald-400/12 via-white/5 to-transparent blur-xl hidden md:block"
          style={{ x: smoothX, y: smoothY, translateX: '-50%', translateY: '-50%' }}
          animate={{
            width: isHoveringInteractive ? 140 : 80,
            height: isHoveringInteractive ? 140 : 80,
            opacity: isMouseInWindow ? 1 : 0,
          }}
          transition={{ type: 'spring', stiffness: 180, damping: 22 }}
        />
      )}

      {/* Dynamic Mouse Background Spotlight (same as Landing Page) */}
      <div
        className="pointer-events-none fixed inset-0 z-0 transition-opacity duration-300 opacity-60 hidden md:block"
        style={{
          background: `radial-gradient(650px circle at ${rawMouse.x}px ${rawMouse.y}px, rgba(255, 255, 255, 0.035), transparent 70%)`,
        }}
      />

      {/* Ambient background glow orbs */}
      <div className="pointer-events-none fixed -top-32 -left-32 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl z-0" />
      <div className="pointer-events-none fixed -bottom-32 right-12 w-96 h-96 bg-teal-500/5 rounded-full blur-3xl z-0" />

      <Sidebar currentDatasetId={selectedDataset?.id} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative z-10">
        <Header
          title={getPageTitle(location.pathname)}
          datasets={datasets}
          selectedDataset={selectedDataset}
          onSelectDataset={onSelectDataset}
        />
        <main className="flex-1 overflow-y-auto p-6 md:p-8 relative">{children}</main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);

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

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedLayout
              selectedDataset={selectedDataset}
              datasets={datasets}
              onSelectDataset={setSelectedDataset}
            >
              <Routes>
                <Route
                  path="/dashboard"
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
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </ProtectedLayout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
};
