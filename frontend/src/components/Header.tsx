import React from 'react';
import { Link } from 'react-router-dom';
import { Database, LogOut, RefreshCw, FileText, Shield } from 'lucide-react';
import { clearAuthToken } from '../api/client';
import { HashBadge } from './HashBadge';
import { Dataset } from '../types';

interface HeaderProps {
  title: string;
  datasets?: Dataset[];
  selectedDataset?: Dataset | null;
  onSelectDataset?: (dataset: Dataset) => void;
  onLoadDemo?: () => void;
  isLoadingDemo?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  datasets = [],
  selectedDataset,
  onSelectDataset,
  onLoadDemo,
  isLoadingDemo = false,
}) => {
  const handleLogout = () => {
    clearAuthToken();
    window.location.href = '/login';
  };

  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between shrink-0 z-10">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-bold text-white tracking-tight">{title}</h2>

        {selectedDataset && (
          <div className="flex items-center gap-2">
            <span className="text-slate-600">/</span>
            <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700/60 rounded-lg px-2.5 py-1 text-xs">
              <Database className="w-3.5 h-3.5 text-indigo-400" />
              <select
                className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer pr-1"
                value={selectedDataset.id}
                onChange={(e) => {
                  const ds = datasets.find((d) => d.id === e.target.value);
                  if (ds && onSelectDataset) onSelectDataset(ds);
                }}
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id} className="bg-slate-900 text-slate-200">
                    {d.filename} ({d.rows} rows, {d.cols} cols)
                  </option>
                ))}
              </select>
            </div>
            <HashBadge originalHash={selectedDataset.canonical_hash} size="sm" />
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        {onLoadDemo && (
          <button
            onClick={onLoadDemo}
            disabled={isLoadingDemo}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 text-xs font-semibold transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingDemo ? 'animate-spin' : ''}`} />
            {isLoadingDemo ? 'Loading Demo...' : 'Load Enterprise Demo'}
          </button>
        )}

        <Link
          to="/"
          title="ShieldSense Landing Page"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-medium transition-colors"
        >
          <Shield className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Landing Page</span>
        </Link>

        <button
          onClick={() => window.open('/docs', '_blank')}
          title="Open API Docs (Swagger)"
          className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
        >
          <FileText className="w-4 h-4" />
        </button>

        <button
          onClick={handleLogout}
          title="Sign Out"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-500/20 hover:text-rose-400 text-slate-400 border border-slate-700/60 text-xs font-medium transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
};
