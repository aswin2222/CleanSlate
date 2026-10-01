import React from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  UploadCloud,
  FileSearch,
  Scale,
  GitPullRequest,
  RotateCcw,
  CheckCircle,
  ShieldAlert,
  BarChart3,
  Activity,
  Shield,
  Zap,
  ArrowRight,
} from 'lucide-react';

interface SidebarProps {
  currentDatasetId?: string | null;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/upload', label: 'Upload Dataset', icon: UploadCloud },
    { to: '/profile', label: 'Dataset Profiler', icon: FileSearch },
    { to: '/rules', label: 'Inferred Rules', icon: Scale },
    { to: '/plan', label: 'Plan & Loss Model', icon: GitPullRequest },
    { to: '/apply', label: 'Apply & Rollback', icon: RotateCcw },
    { to: '/verify', label: 'Test Suite & Pandera', icon: CheckCircle },
    { to: '/adversarial', label: 'Adversarial Lab', icon: ShieldAlert },
    { to: '/benchmarks', label: 'Benchmarks', icon: BarChart3 },
    { to: '/audit', label: 'Audit & Health', icon: Activity },
  ];

  return (
    <aside className="w-64 bg-black/95 backdrop-blur-2xl border-r border-neutral-800/80 flex flex-col shrink-0 select-none z-20 relative">
      {/* Brand Header - Clean Minimalist Brand Pill */}
      <div className="h-16 flex items-center justify-between px-5 border-b border-neutral-800/80 bg-neutral-950/60">
        <NavLink to="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white group-hover:scale-105 transition-transform">
            <Shield className="w-3.5 h-3.5 fill-white stroke-transparent" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-white text-sm font-semibold tracking-tight">TITAN</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-neutral-900 text-neutral-300 border border-neutral-800">
                v1.0
              </span>
            </div>
            <p className="text-[10px] text-neutral-400 font-sans tracking-tight">Autonomous Cleaner</p>
          </div>
        </NavLink>

        <span className="flex items-center gap-1 text-[10px] text-neutral-300 font-mono bg-neutral-900 px-2 py-0.5 rounded-full border border-neutral-800">
          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
          Live
        </span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-500 flex items-center justify-between">
          <span>PIPELINE WORKSPACE</span>
          <span className="text-[9px] font-mono text-neutral-400 tracking-wider">REVERSIBLE</span>
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-xs font-medium transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-neutral-900 text-white border border-neutral-700/80 shadow-sm'
                    : 'text-neutral-400 hover:text-white hover:bg-neutral-900/60'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute left-0 top-2.5 bottom-2.5 w-1 rounded-r-full bg-white" />
                  )}
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-transform duration-200 ${
                      isActive
                        ? 'text-white'
                        : 'group-hover:text-neutral-200 group-hover:scale-105'
                    }`}
                  />
                  <span className="tracking-tight">{item.label}</span>
                </>
              )}
            </NavLink>
          );
        })}

        <div className="pt-3 mt-3 border-t border-neutral-800/80">
          <NavLink
            to="/"
            className="group flex items-center justify-between px-3.5 py-2.5 rounded-2xl text-xs font-medium text-neutral-300 bg-neutral-950 hover:bg-neutral-900 border border-neutral-800 transition-all hover:border-neutral-700"
          >
            <div className="flex items-center gap-2.5">
              <Shield className="w-3.5 h-3.5 text-neutral-400" />
              <span>Back to Landing</span>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-neutral-500 group-hover:text-white transition-colors" />
          </NavLink>
        </div>
      </nav>

      {/* Status Footer */}
      <div className="p-4 border-t border-neutral-800/80 bg-neutral-950/80">
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-neutral-400 text-[11px]">Ledger Engine</span>
          <span className="text-neutral-200 flex items-center gap-1 font-mono text-[10px] bg-neutral-900 px-2 py-0.5 rounded-full border border-neutral-800">
            <span className="w-1.5 h-1.5 rounded-full bg-white" />
            100% Reversible
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-neutral-500 font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" />
          <span className="truncate">SHA-256 Canonical Equality</span>
        </div>
      </div>
    </aside>
  );
};
