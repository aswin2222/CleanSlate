import React from 'react';
import { Link } from 'react-router-dom';
import { Database, LogOut, FileText, Shield, ChevronDown } from 'lucide-react';
import { clearAuthToken, BASE_URL } from '../api/client';
import { Dataset } from '../types';

interface HeaderProps {
  title: string;
  datasets?: Dataset[];
  selectedDataset?: Dataset | null;
  onSelectDataset?: (dataset: Dataset) => void;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  datasets = [],
  selectedDataset,
  onSelectDataset,
}) => {
  const handleLogout = () => {
    clearAuthToken();
    window.location.href = '/login';
  };

  return (
    <header className="h-16 bg-black/90 backdrop-blur-xl border-b border-neutral-800/80 px-6 flex items-center justify-between shrink-0 z-20 relative">
      {/* Left: Clean Breadcrumb & Dataset Selector */}
      <div className="flex items-center gap-3 min-w-0">
        <h2 className="text-sm font-semibold text-white tracking-tight whitespace-nowrap shrink-0">
          {title}
        </h2>

        {selectedDataset && (
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-neutral-600 font-light select-none">/</span>
            <div className="relative flex items-center gap-2 bg-neutral-900/90 border border-neutral-800 hover:border-neutral-700 rounded-full px-3 py-1.5 text-xs transition-colors shadow-sm group min-w-0">
              <Database className="w-3.5 h-3.5 text-white shrink-0 group-hover:scale-105 transition-transform" />
              <select
                className="bg-transparent text-neutral-200 font-medium focus:outline-none cursor-pointer pr-5 appearance-none text-xs truncate max-w-[180px] sm:max-w-[260px] md:max-w-[340px]"
                value={selectedDataset.id}
                onChange={(e) => {
                  const ds = datasets.find((d) => d.id === e.target.value);
                  if (ds && onSelectDataset) onSelectDataset(ds);
                }}
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id} className="bg-neutral-950 text-neutral-200 py-1">
                    {d.filename} ({d.rows} rows, {d.cols} cols)
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3 h-3 text-neutral-400 pointer-events-none absolute right-2.5" />
            </div>
          </div>
        )}
      </div>

      {/* Right: Clean, Uncluttered Utility Actions */}
      <div className="flex items-center gap-2.5 shrink-0">
        <Link
          to="/"
          title="Return to Landing Page"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-neutral-300 hover:text-white border border-neutral-800 text-xs font-medium transition-colors"
        >
          <Shield className="w-3.5 h-3.5 text-white" />
          <span className="hidden sm:inline">Landing Page</span>
        </Link>

        <button
          onClick={() => window.open(`${BASE_URL || 'http://127.0.0.1:8000'}/docs`, '_blank')}
          title="Open API Docs (Swagger)"
          className="p-1.5 px-2.5 rounded-full bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 text-neutral-400 hover:text-white transition-colors cursor-pointer flex items-center gap-1 text-xs"
        >
          <FileText className="w-3.5 h-3.5 text-white" />
          <span className="hidden md:inline">API</span>
        </button>

        <button
          onClick={handleLogout}
          title="Sign Out"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-neutral-300 hover:text-white border border-neutral-800 text-xs font-medium transition-colors cursor-pointer"
        >
          <LogOut className="w-3.5 h-3.5 text-white" />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
};
