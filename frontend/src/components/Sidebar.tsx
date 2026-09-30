import React from 'react';
import { NavLink } from 'react-router-dom';
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
  Sparkles,
} from 'lucide-react';

interface SidebarProps {
  currentDatasetId?: string | null;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
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
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 select-none">
      {/* Brand header */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-slate-800 bg-slate-900/50">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20 font-black text-xl tracking-wider">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-white text-base tracking-tight leading-none flex items-center gap-1.5">
            CleanSlate
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              v1.0
            </span>
          </h1>
          <p className="text-[11px] text-slate-400 font-medium mt-1">Autonomous Data Cleaner</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          CleanSlate Pipeline
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Status Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/60">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="text-slate-400">Ledger Engine</span>
          <span className="text-emerald-400 flex items-center gap-1 font-mono text-[11px]">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Reversible
          </span>
        </div>
        <div className="text-[11px] text-slate-500 font-mono truncate">
          SHA-256 Canonical Equality
        </div>
      </div>
    </aside>
  );
};
