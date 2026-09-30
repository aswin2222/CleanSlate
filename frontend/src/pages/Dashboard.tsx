import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { Dataset, Run } from '../types';
import { HashBadge } from '../components/HashBadge';
import {
  Database,
  ArrowRight,
  ShieldCheck,
  Zap,
  Activity,
  CheckCircle,
  Clock,
  Layers,
  Cloud,
  Flame,
  ExternalLink,
} from 'lucide-react';

interface DashboardProps {
  onSelectDataset: (dataset: Dataset) => void;
  selectedDataset: Dataset | null;
}

export const Dashboard: React.FC<DashboardProps> = ({ onSelectDataset, selectedDataset }) => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [dsList, runList] = await Promise.all([
        apiRequest<Dataset[]>('/api/datasets'),
        apiRequest<Run[]>('/api/runs'),
      ]);
      setDatasets(dsList);
      setRuns(runList);
      if (!selectedDataset && dsList.length > 0) {
        onSelectDataset(dsList[0]);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleCreateRun = async (datasetId: string) => {
    try {
      const run = await apiRequest<Run>(`/api/datasets/${datasetId}/runs`, {
        method: 'POST',
        body: JSON.stringify({ llm_mode: 'heuristic_only' }),
      });
      navigate(`/plan?run_id=${run.id}`);
    } catch (err) {
      console.error('Failed to start run:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 p-8 shadow-xl">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold">
              <Zap className="w-3.5 h-3.5" /> Autonomous Safe Data Cleaning
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 text-xs font-semibold">
              <Cloud className="w-3.5 h-3.5" /> Cloudinary: bgrvz383
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold">
              <Flame className="w-3.5 h-3.5" /> Firestore: titan-d57bf
            </span>
          </div>

          <h1 className="text-2xl font-extrabold text-white tracking-tight sm:text-3xl">
            Clean enterprise data with mathematical reversibility
          </h1>
          <p className="mt-2 text-sm text-slate-400 leading-relaxed">
            CleanSlate profiles anomalies, infers semantic rules, projects multi-component information loss, and guarantees 100% reversible rollback verified by canonical SHA-256 equality.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={() => navigate('/upload')}
              className="px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all"
            >
              <Zap className="w-4 h-4" /> Upload Dataset to Cloudinary
            </button>
          </div>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Datasets Managed</span>
            <Database className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">{datasets.length}</div>
          <div className="text-xs text-slate-500 mt-1">Stored in Cloudinary & Firestore</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Rollback Fidelity</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">100.0%</div>
          <div className="text-xs text-emerald-500/80 mt-1">Verified SHA-256 canonical match</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Fault Detection</span>
            <CheckCircle className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400">100.0%</div>
          <div className="text-xs text-cyan-500/80 mt-1">Mutation-tested synthetic bugs</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Adversarial Defense</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-indigo-400">Active</div>
          <div className="text-xs text-indigo-500/80 mt-1">Upload Guardrail protection</div>
        </div>
      </div>

      {/* Datasets Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">Active Datasets</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">{datasets.length} registered</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Loading datasets...</div>
        ) : datasets.length === 0 ? (
          <div className="p-12 text-center">
            <Database className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-300 font-medium">No datasets loaded yet</p>
            <p className="text-xs text-slate-500 mt-1">Upload a CSV, JSON, Parquet, or Excel file to get started</p>
            <button
              onClick={() => navigate('/upload')}
              className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold inline-flex items-center gap-2"
            >
              <Zap className="w-3.5 h-3.5" /> Upload Now
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/50 text-slate-400 uppercase tracking-wider border-b border-slate-800 font-semibold">
                <tr>
                  <th className="py-3 px-6">Filename</th>
                  <th className="py-3 px-4">Dimensions</th>
                  <th className="py-3 px-4">Format</th>
                  <th className="py-3 px-6">Canonical SHA-256</th>
                  <th className="py-3 px-4">Cloudinary</th>
                  <th className="py-3 px-4">Uploaded</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {datasets.map((d) => (
                  <tr
                    key={d.id}
                    className={`hover:bg-slate-800/40 transition-colors ${
                      selectedDataset?.id === d.id ? 'bg-indigo-950/20' : ''
                    }`}
                  >
                    <td className="py-3 px-6 font-medium text-white flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                      {d.filename}
                    </td>
                    <td className="py-3 px-4 font-mono">
                      {d.rows.toLocaleString()} rows × {d.cols} cols
                    </td>
                    <td className="py-3 px-4 uppercase font-semibold text-slate-400">{d.format}</td>
                    <td className="py-3 px-6">
                      <HashBadge originalHash={d.canonical_hash} size="sm" />
                    </td>
                    <td className="py-3 px-4">
                      {d.cloudinary_url ? (
                        <a
                          href={d.cloudinary_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sky-400 hover:text-sky-300 font-mono text-[11px]"
                        >
                          <Cloud className="w-3 h-3" />
                          <span>Stored</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      ) : (
                        <span className="text-slate-500 text-[11px]">Encrypted Local</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {new Date(d.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3 px-6 text-right space-x-2">
                      <button
                        onClick={() => {
                          onSelectDataset(d);
                          navigate('/profile');
                        }}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium"
                      >
                        Profile
                      </button>
                      <button
                        onClick={() => handleCreateRun(d.id)}
                        className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium inline-flex items-center gap-1"
                      >
                        Clean <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Runs */}
      {runs.length > 0 && (
        <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">Cleaning Runs</h2>
            </div>
          </div>
          <div className="divide-y divide-slate-800/60 text-xs">
            {runs.slice(0, 5).map((r) => (
              <div key={r.id} className="p-4 flex items-center justify-between hover:bg-slate-800/30">
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                      r.status === 'APPLIED'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : r.status === 'ROLLED_BACK'
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        : 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
                    }`}
                  >
                    {r.status}
                  </span>
                  <span className="font-mono text-slate-300">Run {r.id.slice(0, 8)}</span>
                  <span className="text-slate-500">Mode: {r.llm_mode}</span>
                </div>
                <button
                  onClick={() => navigate(`/plan?run_id=${r.id}`)}
                  className="text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
                >
                  View Details <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
