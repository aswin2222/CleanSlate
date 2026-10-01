import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { apiRequest } from '../api/client';
import { Dataset, DatasetProfile, ColumnProfile } from '../types';
import {
  FileSearch,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  Layers,
  Fingerprint,
  BarChart2,
  CheckCircle2,
  TrendingDown,
  Hash,
  Database,
} from 'lucide-react';

interface ProfileProps {
  selectedDataset: Dataset | null;
}

export const Profile: React.FC<ProfileProps> = ({ selectedDataset }) => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedCol, setSelectedCol] = useState<ColumnProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedDataset) return;
    const fetchProfile = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiRequest<DatasetProfile>(`/api/datasets/${selectedDataset.id}/profile`);
        setProfile(data);
        const firstColName = Object.keys(data.columns)[0];
        if (firstColName) {
          setSelectedCol(data.columns[firstColName]);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [selectedDataset]);

  if (!selectedDataset) {
    return (
      <div className="p-16 text-center bg-neutral-950 border border-neutral-800 rounded-3xl">
        <FileSearch className="w-12 h-12 text-neutral-600 mx-auto mb-3" />
        <h3 className="text-white font-semibold text-base">No dataset selected</h3>
        <p className="text-xs text-neutral-400 mt-1">Please select or upload a dataset first</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-16 text-center text-neutral-400 text-sm flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        <span>Analyzing data patterns, format variants, and outlier distributions...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8 relative">
      {/* Top Bar with actions */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 shadow-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-6 relative overflow-hidden"
      >
        <div className="pointer-events-none absolute -right-10 -bottom-10 w-48 h-48 bg-cyan-500/10 rounded-full blur-2xl" />

        <div className="space-y-2 z-10">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider bg-neutral-900 text-neutral-300 border border-neutral-800">
              Chunked Profiler
            </span>
            <span className="font-mono text-xs text-neutral-400 bg-neutral-900 px-2.5 py-0.5 rounded-full border border-neutral-800">
              {selectedDataset.filename}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight uppercase">
            Deterministic Dataset Profiler
          </h1>
          <p className="text-xs text-neutral-400 leading-relaxed max-w-xl">
            Computes column types, sparsity rates, regex pattern signatures, and statistical distributions.
          </p>
        </div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => navigate('/rules')}
          className="px-6 py-2.5 rounded-full bg-white text-black font-semibold text-xs flex items-center gap-2 hover:bg-neutral-200 transition-all shadow-md shrink-0 self-start sm:self-center cursor-pointer z-10"
        >
          <Sparkles className="w-4 h-4 fill-black" />
          <span>Infer Semantic Rules</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </motion.button>
      </motion.div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-2xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs flex items-center gap-2.5"
        >
          <AlertTriangle className="w-5 h-5 shrink-0 text-red-400" />
          <span>{error}</span>
        </motion.div>
      )}

      {profile && (
        <>
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <motion.div
              whileHover={{ y: -4 }}
              className="card-flow-bg p-5 rounded-3xl bg-neutral-950 border border-neutral-800/90 relative overflow-hidden"
            >
              <div className="text-neutral-400 text-[10px] uppercase font-bold tracking-wider font-mono">Total Rows</div>
              <div className="text-2xl font-extrabold font-mono text-white mt-1.5">
                {profile.total_rows.toLocaleString()}
              </div>
            </motion.div>

            <motion.div
              whileHover={{ y: -4 }}
              className="card-flow-bg p-5 rounded-3xl bg-neutral-950 border border-neutral-800/90 relative overflow-hidden"
            >
              <div className="text-neutral-400 text-[10px] uppercase font-bold tracking-wider font-mono">Columns</div>
              <div className="text-2xl font-extrabold font-mono text-white mt-1.5">
                {profile.total_columns}
              </div>
            </motion.div>

            <motion.div
              whileHover={{ y: -4, scale: 1.01 }}
              className="card-flow-bg p-5 rounded-3xl bg-neutral-950 border border-neutral-800/90 relative overflow-hidden"
            >
              <div className="text-neutral-400 text-[10px] uppercase font-bold tracking-wider font-mono">Exact Duplicates</div>
              <div className="text-2xl font-extrabold font-mono text-amber-400 mt-1.5">
                {profile.exact_duplicate_rows}
              </div>
            </motion.div>

            <motion.div
              whileHover={{ y: -4, scale: 1.01 }}
              className="card-flow-bg p-5 rounded-3xl bg-neutral-950 border border-neutral-800/90 relative overflow-hidden"
            >
              <div className="text-neutral-400 text-[10px] uppercase font-bold tracking-wider font-mono">Near Duplicates</div>
              <div className="text-2xl font-extrabold font-mono text-teal-400 mt-1.5">
                {profile.near_duplicate_candidates_count}
              </div>
            </motion.div>

            <motion.div
              whileHover={{ y: -4, scale: 1.01 }}
              className="card-flow-bg p-5 rounded-3xl bg-neutral-950 border border-neutral-800/90 relative overflow-hidden"
            >
              <div className="text-neutral-400 text-[10px] uppercase font-bold tracking-wider font-mono">Dataset Sparsity</div>
              <div className="text-2xl font-extrabold font-mono text-white mt-1.5">
                {(profile.sparsity_report.dataset_sparsity_rate * 100).toFixed(1)}%
              </div>
            </motion.div>
          </div>

          {/* Low Evidence / Sparsity Alert */}
          {profile.sparsity_report.is_low_evidence && (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-3xl bg-neutral-950 border border-amber-500/30 text-amber-200 text-xs flex items-center gap-3 shadow-lg"
            >
              <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400" />
              <span>
                <strong>Low Evidence Alert:</strong> High sparsity detected (
                {(profile.sparsity_report.dataset_sparsity_rate * 100).toFixed(1)}%). Conservative rule inference thresholds automatically engaged.
              </span>
            </motion.div>
          )}

          {/* Main Layout: Column Table on Left, Selected Column Detail on Right */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Columns List Table */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="lg:col-span-2 rounded-3xl bg-neutral-950 border border-neutral-800/90 overflow-hidden shadow-2xl"
            >
              <div className="px-6 py-5 border-b border-neutral-800/80 flex items-center justify-between bg-neutral-900/60">
                <span className="text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-neutral-300" /> Column Catalog ({profile.total_columns})
                </span>
                <span className="text-xs text-neutral-400 font-sans">Click a row to inspect distributions</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-neutral-900/60 text-neutral-400 uppercase tracking-wider border-b border-neutral-800/80 font-mono text-[11px]">
                    <tr>
                      <th className="py-3.5 px-5">Column</th>
                      <th className="py-3.5 px-4">Primary Type</th>
                      <th className="py-3.5 px-4">Null Rate</th>
                      <th className="py-3.5 px-4">Distinct</th>
                      <th className="py-3.5 px-4">Outliers</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-850 font-sans">
                    {Object.values(profile.columns).map((col) => {
                      const isSelected = selectedCol?.column_name === col.column_name;
                      return (
                        <tr
                          key={col.column_name}
                          onClick={() => setSelectedCol(col)}
                          className={`cursor-pointer transition-colors group ${
                            isSelected
                              ? 'bg-neutral-900/60 text-white font-medium'
                              : 'hover:bg-neutral-900/40 text-neutral-300'
                          }`}
                        >
                          <td className="py-3.5 px-5 flex items-center gap-2.5 font-mono">
                            <span
                              className={`w-2 h-2 rounded-full ${
                                col.is_mixed_type
                                  ? 'bg-amber-400'
                                  : 'bg-white'
                              }`}
                            />
                            <span className="font-semibold text-white group-hover:text-white transition-colors">
                              {col.column_name}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-neutral-900 border border-neutral-800 text-neutral-300">
                              {col.primary_type}
                            </span>
                            {col.is_mixed_type && (
                              <span
                                className="ml-1.5 px-2 py-0.2 rounded-full text-[9px] bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30"
                                title="Mixed data types detected"
                              >
                                MIXED
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-2.5">
                              <div className="w-16 h-1.5 bg-neutral-900 rounded-full overflow-hidden border border-neutral-800">
                                <div
                                  className={`h-full rounded-full ${
                                    col.null_rate > 0.3
                                      ? 'bg-red-500'
                                      : col.null_rate > 0.05
                                      ? 'bg-amber-500'
                                      : 'bg-neutral-400'
                                  }`}
                                  style={{ width: `${Math.round(col.null_rate * 100)}%` }}
                                />
                              </div>
                              <span className="font-mono text-neutral-400 text-[11px]">
                                {(col.null_rate * 100).toFixed(1)}%
                              </span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4 font-mono text-neutral-300">{col.distinct_count}</td>
                          <td className="py-3.5 px-4 font-mono">
                            {col.iqr_outliers_count > 0 ? (
                              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                {col.iqr_outliers_count} IQR
                              </span>
                            ) : (
                              <span className="text-neutral-500">0</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </motion.div>

            {/* Selected Column Deep Profile */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="rounded-3xl bg-neutral-950 border border-neutral-800/90 p-6 space-y-5 shadow-2xl"
            >
              {selectedCol ? (
                <>
                  <div className="border-b border-neutral-800/80 pb-4">
                    <div className="text-[10px] uppercase tracking-wider text-neutral-400 font-mono font-semibold flex items-center gap-1.5">
                      <Fingerprint className="w-3.5 h-3.5 text-neutral-400" />
                      Detailed Column Inspector
                    </div>
                    <h3 className="text-lg font-semibold text-white font-mono mt-1 tracking-tight">
                      {selectedCol.column_name}
                    </h3>
                  </div>

                  {/* Type distribution breakdown */}
                  <div>
                    <div className="text-xs font-semibold text-neutral-300 mb-2 flex items-center justify-between">
                      <span>Type Distribution</span>
                      <span className="text-[10px] text-neutral-500 font-mono">INFERRED</span>
                    </div>
                    <div className="space-y-1.5 text-xs font-mono">
                      {Object.entries(selectedCol.inferred_types).map(([t, count]) => (
                        <div
                          key={t}
                          className="flex justify-between items-center bg-neutral-900/80 px-3 py-1.5 rounded-xl border border-neutral-800"
                        >
                          <span className="text-neutral-300">{t}</span>
                          <span className="text-white font-bold">
                            {count}{' '}
                            <span className="text-neutral-500 text-[10px] font-normal">
                              ({Math.round((count / selectedCol.total_count) * 100)}%)
                            </span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Anomalies Detected */}
                  <div className="space-y-2 pt-3 border-t border-neutral-800/80 text-xs">
                    <div className="font-semibold text-white text-xs">Anomalies Detected</div>
                    <div className="grid grid-cols-2 gap-2.5">
                      <div className="bg-neutral-900/80 p-3 rounded-2xl border border-neutral-800">
                        <div className="text-neutral-500 text-[10px] uppercase font-bold font-mono">Whitespace</div>
                        <div className="font-mono font-bold text-white mt-0.5">
                          {selectedCol.leading_trailing_whitespace_count}
                        </div>
                      </div>
                      <div className="bg-neutral-900/80 p-3 rounded-2xl border border-neutral-800">
                        <div className="text-neutral-500 text-[10px] uppercase font-bold font-mono">Case Drift</div>
                        <div className="font-mono font-bold text-white mt-0.5">
                          {selectedCol.case_inconsistencies}
                        </div>
                      </div>
                      <div className="bg-neutral-900/80 p-3 rounded-2xl border border-neutral-800">
                        <div className="text-neutral-500 text-[10px] uppercase font-bold font-mono">IQR Outliers</div>
                        <div className="font-mono font-bold text-amber-300 mt-0.5">
                          {selectedCol.iqr_outliers_count}
                        </div>
                      </div>
                      <div className="bg-neutral-900/80 p-3 rounded-2xl border border-neutral-800">
                        <div className="text-neutral-500 text-[10px] uppercase font-bold font-mono">MAD Outliers</div>
                        <div className="font-mono font-bold text-amber-300 mt-0.5">
                          {selectedCol.mad_outliers_count}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Numeric Stats if applicable */}
                  {selectedCol.is_numeric && selectedCol.mean !== undefined && (
                    <div className="pt-3 border-t border-neutral-800/80 text-xs space-y-2">
                      <div className="font-semibold text-white">Numeric Summary</div>
                      <div className="grid grid-cols-2 gap-2 text-neutral-300 font-mono text-[11px] bg-neutral-900/80 p-3 rounded-2xl border border-neutral-800">
                        <div>Min: {selectedCol.min_value?.toFixed(2)}</div>
                        <div>Max: {selectedCol.max_value?.toFixed(2)}</div>
                        <div>Mean: {selectedCol.mean?.toFixed(2)}</div>
                        <div>Median: {selectedCol.median?.toFixed(2)}</div>
                      </div>
                    </div>
                  )}

                  {/* Top Patterns */}
                  {selectedCol.pattern_signatures && selectedCol.pattern_signatures.length > 0 && (
                    <div className="pt-3 border-t border-neutral-800/80 text-xs">
                      <div className="font-semibold text-white mb-2">Top Regex Signatures</div>
                      <div className="space-y-1.5 font-mono text-[11px]">
                        {selectedCol.pattern_signatures.slice(0, 3).map(([pat, c], i) => (
                          <div
                            key={i}
                            className="truncate bg-neutral-900/80 px-3 py-1.5 rounded-xl border border-neutral-800 text-neutral-300"
                          >
                            <span className="text-white font-mono">{pat}</span>{' '}
                            <span className="text-neutral-500">({c})</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-neutral-500 text-xs text-center py-10">Select a column to inspect</div>
              )}
            </motion.div>
          </div>
        </>
      )}
    </div>
  );
};
