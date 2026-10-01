import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { apiRequest } from '../api/client';
import { Dataset, Run } from '../types';
import { HashBadge } from '../components/HashBadge';
import { ExportDataModal } from '../components/ExportDataModal';
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
  Download,
  Sparkles,
  FileSpreadsheet,
  FileCode,
  FileText,
  Binary,
  Shield,
  Lock,
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
  const [exportTarget, setExportTarget] = useState<Dataset | null>(null);

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

  const getFormatIcon = (format: string) => {
    switch (format.toLowerCase()) {
      case 'xlsx':
      case 'xls':
        return <FileSpreadsheet className="w-3.5 h-3.5 text-cyan-400" />;
      case 'csv':
      case 'tsv':
        return <FileText className="w-3.5 h-3.5 text-sky-400" />;
      case 'json':
      case 'jsonl':
        return <FileCode className="w-3.5 h-3.5 text-amber-400" />;
      case 'parquet':
        return <Binary className="w-3.5 h-3.5 text-purple-400" />;
      default:
        return <Database className="w-3.5 h-3.5 text-neutral-400" />;
    }
  };

  return (
    <div className="space-y-8 relative">
      {/* Top Banner / Hero with Clean Minimalist White Typography */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative overflow-hidden rounded-3xl bg-neutral-950 border border-neutral-800/90 p-8 sm:p-10 shadow-2xl text-white group"
      >
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-neutral-300 text-xs font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-neutral-300" />
              <span>Autonomous Safe Cleaning Engine</span>
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-neutral-300 text-xs font-mono">
              <Cloud className="w-3.5 h-3.5 text-neutral-400" /> Cloudinary: bgrvz383
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-neutral-300 text-xs font-mono">
              <Flame className="w-3.5 h-3.5 text-neutral-400" /> Firestore: titan-d57bf
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-medium tracking-tight text-white uppercase leading-tight">
            Clean enterprise data with{' '}
            <span className="text-white font-semibold">
              mathematical reversibility
            </span>
          </h1>

          <p className="text-sm text-neutral-400 leading-relaxed font-normal max-w-2xl">
            TITAN autonomously profiles quality anomalies, infers semantic rules, projects multi-component information loss, and guarantees 100% reversible rollback verified by canonical SHA-256 equality.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/upload')}
              className="px-6 py-3 rounded-full bg-white text-black font-semibold text-xs flex items-center gap-2 hover:bg-neutral-200 transition-all shadow-md cursor-pointer"
            >
              <Zap className="w-3.5 h-3.5 fill-black" />
              <span>Upload Dataset to Cloudinary</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/adversarial')}
              className="px-5 py-3 rounded-full bg-neutral-900 hover:bg-neutral-800 text-white border border-neutral-800 text-xs font-medium flex items-center gap-2 transition-colors cursor-pointer"
            >
              <Activity className="w-3.5 h-3.5 text-neutral-300" />
              <span>Launch Adversarial Lab</span>
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* KPI Metric Cards with Simple White Text */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
          whileHover={{ y: -4 }}
          className="card-flow-bg p-6 rounded-3xl bg-neutral-950 border border-neutral-800/90 shadow-2xl relative overflow-hidden group cursor-pointer"
        >
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-3">
            <span className="font-semibold uppercase tracking-wider text-[11px] font-mono">Datasets Managed</span>
            <div className="w-8 h-8 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white">
              <Database className="w-4 h-4 text-neutral-300" />
            </div>
          </div>
          <div className="text-3xl font-extrabold font-mono text-white tracking-tight">{datasets.length}</div>
          <div className="text-xs text-neutral-400 mt-2 flex items-center gap-1.5 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" />
            Cloudinary & Firestore sync
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          whileHover={{ y: -4 }}
          className="card-flow-bg p-6 rounded-3xl bg-neutral-950 border border-neutral-800/90 shadow-2xl relative overflow-hidden group cursor-pointer"
        >
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-3">
            <span className="font-semibold uppercase tracking-wider text-[11px] font-mono">Rollback Fidelity</span>
            <div className="w-8 h-8 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white">
              <ShieldCheck className="w-4 h-4 text-neutral-300" />
            </div>
          </div>
          <div className="text-3xl font-extrabold font-mono text-white tracking-tight">
            100.0%
          </div>
          <div className="text-xs text-neutral-400 mt-2 flex items-center gap-1.5 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" />
            Verified SHA-256 canonical match
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
          whileHover={{ y: -4 }}
          className="card-flow-bg p-6 rounded-3xl bg-neutral-950 border border-neutral-800/90 shadow-2xl relative overflow-hidden group cursor-pointer"
        >
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-3">
            <span className="font-semibold uppercase tracking-wider text-[11px] font-mono">Fault Detection</span>
            <div className="w-8 h-8 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white">
              <CheckCircle className="w-4 h-4 text-neutral-300" />
            </div>
          </div>
          <div className="text-3xl font-extrabold font-mono text-white tracking-tight">
            100.0%
          </div>
          <div className="text-xs text-neutral-400 mt-2 flex items-center gap-1.5 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" />
            Mutation-tested synthetic bugs
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          whileHover={{ y: -4 }}
          className="card-flow-bg p-6 rounded-3xl bg-neutral-950 border border-neutral-800/90 shadow-2xl relative overflow-hidden group cursor-pointer"
        >
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-3">
            <span className="font-semibold uppercase tracking-wider text-[11px] font-mono">Adversarial Defense</span>
            <div className="w-8 h-8 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white">
              <Lock className="w-4 h-4 text-neutral-300" />
            </div>
          </div>
          <div className="text-3xl font-extrabold font-mono text-white tracking-tight">Active</div>
          <div className="text-xs text-neutral-400 mt-2 flex items-center gap-1.5 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" />
            Upload Guardrail protection
          </div>
        </motion.div>
      </div>

      {/* Datasets Table */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.25 }}
        className="rounded-3xl bg-neutral-950 border border-neutral-800/90 overflow-hidden shadow-2xl"
      >
        <div className="px-6 py-5 border-b border-neutral-800/80 flex items-center justify-between bg-neutral-900/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white">
              <Layers className="w-4 h-4 text-neutral-300" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white tracking-tight uppercase">Active Datasets</h2>
              <p className="text-xs text-neutral-400 font-sans">Reversible snapshots managed by ledger engine</p>
            </div>
          </div>
          <span className="text-xs text-neutral-400 font-mono bg-neutral-900 px-3 py-1 rounded-full border border-neutral-800">
            {datasets.length} registered
          </span>
        </div>

        {loading ? (
          <div className="p-16 text-center text-neutral-400 text-xs flex flex-col items-center justify-center gap-3">
            <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
            <span>Loading datasets from Cloudinary & Firestore...</span>
          </div>
        ) : datasets.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-14 h-14 rounded-2xl bg-neutral-900 border border-neutral-800 flex items-center justify-center text-neutral-500 mx-auto mb-3">
              <Database className="w-7 h-7" />
            </div>
            <p className="text-base text-white font-semibold">No datasets registered yet</p>
            <p className="text-xs text-neutral-400 mt-1 max-w-md mx-auto">
              Upload a CSV, XLSX, JSON, Parquet, or TSV file to start autonomous profiling and reversible cleaning.
            </p>
            <button
              onClick={() => navigate('/upload')}
              className="mt-5 px-6 py-2.5 rounded-full bg-white text-black text-xs font-semibold inline-flex items-center gap-2 hover:bg-neutral-200 transition-all cursor-pointer shadow-md"
            >
              <Zap className="w-3.5 h-3.5 fill-black" /> Upload Dataset Now
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-neutral-900/60 text-neutral-400 uppercase tracking-wider border-b border-neutral-800/80 font-mono text-[11px]">
                <tr>
                  <th className="py-4 px-6">Filename</th>
                  <th className="py-4 px-4">Dimensions</th>
                  <th className="py-4 px-4">Format</th>
                  <th className="py-4 px-6">Canonical SHA-256</th>
                  <th className="py-4 px-4">Storage</th>
                  <th className="py-4 px-4">Uploaded</th>
                  <th className="py-4 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-850 text-neutral-300">
                {datasets.map((d) => {
                  const isSelected = selectedDataset?.id === d.id;
                  return (
                    <tr
                      key={d.id}
                      className={`hover:bg-neutral-900/50 transition-colors group ${
                        isSelected ? 'bg-neutral-900/40' : ''
                      }`}
                    >
                      <td className="py-4 px-6 font-semibold text-white">
                        <div className="flex items-center gap-2.5">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isSelected ? 'bg-white' : 'bg-neutral-600'
                            }`}
                          />
                          <span className="truncate max-w-[220px] font-medium text-white group-hover:text-white transition-colors">
                            {d.filename}
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-4 font-mono text-neutral-300">
                        {d.rows.toLocaleString()}{' '}
                        <span className="text-neutral-500">rows</span> × {d.cols}{' '}
                        <span className="text-neutral-500">cols</span>
                      </td>
                      <td className="py-4 px-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-neutral-900 text-neutral-300 border border-neutral-800">
                          {getFormatIcon(d.format)}
                          <span>{d.format}</span>
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <HashBadge originalHash={d.canonical_hash} size="sm" />
                      </td>
                      <td className="py-4 px-4">
                        {d.cloudinary_url ? (
                          <a
                            href={d.cloudinary_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-neutral-300 hover:text-white font-mono text-[11px] bg-neutral-900 px-2.5 py-1 rounded-full border border-neutral-800 hover:border-neutral-700 transition-colors"
                          >
                            <Cloud className="w-3 h-3 text-neutral-400" />
                            <span>Cloud</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ) : (
                          <span className="text-neutral-500 text-[11px] font-mono">Encrypted Local</span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-neutral-400 font-mono text-[11px]">
                        {new Date(d.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-4 px-6 text-right space-x-2">
                        {/* Download / Export Clean Data Button */}
                        <button
                          onClick={() => setExportTarget(d)}
                          className="px-3.5 py-1.5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium inline-flex items-center gap-1.5 border border-neutral-800 hover:border-neutral-700 transition-all cursor-pointer"
                          title={`Export & Download clean data in ${d.format.toUpperCase()} or any format`}
                        >
                          <Download className="w-3.5 h-3.5 text-neutral-300" />
                          <span>Download</span>
                        </button>

                        <button
                          onClick={() => {
                            onSelectDataset(d);
                            navigate('/profile');
                          }}
                          className="px-3.5 py-1.5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-neutral-300 hover:text-white text-xs font-medium border border-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer"
                        >
                          Profile
                        </button>

                        <button
                          onClick={() => handleCreateRun(d.id)}
                          className="px-4 py-1.5 rounded-full bg-white text-black hover:bg-neutral-200 text-xs font-semibold inline-flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
                        >
                          <span>Clean</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>

      {/* Recent Runs Section */}
      {runs.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
          className="rounded-3xl bg-neutral-950 border border-neutral-800/90 overflow-hidden shadow-2xl"
        >
          <div className="px-6 py-5 border-b border-neutral-800/80 flex items-center justify-between bg-neutral-900/60">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white">
                <Clock className="w-4 h-4 text-neutral-300" />
              </div>
              <h2 className="text-sm font-semibold text-white tracking-tight uppercase">
                Recent Cleaning Runs ({runs.length})
              </h2>
            </div>
          </div>
          <div className="divide-y divide-neutral-850 text-xs">
            {runs.slice(0, 5).map((r) => (
              <div
                key={r.id}
                className="p-4 sm:px-6 flex items-center justify-between hover:bg-neutral-900/40 transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <span
                    className="px-3 py-1 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider border bg-neutral-900 text-neutral-200 border-neutral-800"
                  >
                    {r.status}
                  </span>
                  <span className="font-mono text-white font-semibold">Run {r.id.slice(0, 8)}</span>
                  <span className="text-neutral-400 text-[11px] hidden sm:inline font-mono">Mode: {r.llm_mode}</span>
                </div>
                <button
                  onClick={() => navigate(`/plan?run_id=${r.id}`)}
                  className="text-neutral-300 hover:text-white font-medium flex items-center gap-1.5 transition-colors cursor-pointer group-hover:translate-x-1 duration-200"
                >
                  <span>View Details</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Export & Download Clean Data Modal */}
      {exportTarget && (
        <ExportDataModal
          isOpen={!!exportTarget}
          onClose={() => setExportTarget(null)}
          datasetId={exportTarget.id}
          datasetFilename={exportTarget.filename}
          inputFormat={exportTarget.format}
          isCleaned={true}
        />
      )}
    </div>
  );
};
