import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { Dataset, DatasetProfile, ColumnProfile } from '../types';
import {
  FileSearch,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  Layers,
  Fingerprint,
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
      <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl">
        <FileSearch className="w-12 h-12 text-slate-600 mx-auto mb-3" />
        <h3 className="text-white font-semibold text-sm">No dataset selected</h3>
        <p className="text-xs text-slate-400 mt-1">Please select or upload a dataset first</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400 text-sm">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Analyzing data patterns, format variants, and outlier distributions...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Bar with actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Dataset Profiler: <span className="text-indigo-400 font-mono">{selectedDataset.filename}</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic chunked profiling of types, sparsity, pattern signatures, and statistical distributions.
          </p>
        </div>

        <button
          onClick={() => navigate('/rules')}
          className="px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all shrink-0 self-start"
        >
          <Sparkles className="w-4 h-4" />
          <span>Infer Semantic Rules</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
          {error}
        </div>
      )}

      {profile && (
        <>
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-slate-400 text-xs">Total Rows</div>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {profile.total_rows.toLocaleString()}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-slate-400 text-xs">Columns</div>
              <div className="text-xl font-bold font-mono text-white mt-1">{profile.total_columns}</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-slate-400 text-xs">Exact Duplicates</div>
              <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                {profile.exact_duplicate_rows}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-slate-400 text-xs">Near Duplicates</div>
              <div className="text-xl font-bold font-mono text-cyan-400 mt-1">
                {profile.near_duplicate_candidates_count}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-slate-400 text-xs">Dataset Sparsity</div>
              <div className="text-xl font-bold font-mono text-indigo-400 mt-1">
                {(profile.sparsity_report.dataset_sparsity_rate * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Low Evidence / Sparsity Alert */}
          {profile.sparsity_report.is_low_evidence && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>
                <strong>Low Evidence Alert:</strong> High sparsity detected (
                {(profile.sparsity_report.dataset_sparsity_rate * 100).toFixed(1)}%). Conservative rule inference thresholds automatically engaged.
              </span>
            </div>
          )}

          {/* Main Layout: Column Table on Left, Selected Column Detail on Right */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Columns List Table */}
            <div className="lg:col-span-2 rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
              <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <Layers className="w-3.5 h-3.5 text-indigo-400" /> Columns ({profile.total_columns})
                </span>
                <span className="text-[11px] text-slate-500">Click a column to inspect deep profile</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-4">Column</th>
                      <th className="py-2.5 px-3">Primary Type</th>
                      <th className="py-2.5 px-4">Null Rate</th>
                      <th className="py-2.5 px-3">Distinct</th>
                      <th className="py-2.5 px-3">Outliers</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {Object.values(profile.columns).map((col) => {
                      const isSelected = selectedCol?.column_name === col.column_name;
                      return (
                        <tr
                          key={col.column_name}
                          onClick={() => setSelectedCol(col)}
                          className={`cursor-pointer transition-colors ${
                            isSelected ? 'bg-indigo-950/40 text-white font-medium' : 'hover:bg-slate-800/30 text-slate-300'
                          }`}
                        >
                          <td className="py-2.5 px-4 flex items-center gap-2 font-mono">
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                col.is_mixed_type ? 'bg-amber-400' : 'bg-emerald-400'
                              }`}
                            />
                            {col.column_name}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                              {col.primary_type}
                            </span>
                            {col.is_mixed_type && (
                              <span className="ml-1 text-[10px] text-amber-400 font-semibold" title="Mixed data types found in column">
                                MIXED
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-4">
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    col.null_rate > 0.3 ? 'bg-rose-500' : col.null_rate > 0.05 ? 'bg-amber-500' : 'bg-emerald-500'
                                  }`}
                                  style={{ width: `${Math.round(col.null_rate * 100)}%` }}
                                />
                              </div>
                              <span className="font-mono text-slate-400">
                                {(col.null_rate * 100).toFixed(1)}%
                              </span>
                            </div>
                          </td>
                          <td className="py-2.5 px-3 font-mono">{col.distinct_count}</td>
                          <td className="py-2.5 px-3 font-mono text-slate-400">
                            {col.iqr_outliers_count > 0 ? (
                              <span className="text-amber-400 font-semibold">{col.iqr_outliers_count}</span>
                            ) : (
                              '0'
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Selected Column Deep Profile */}
            <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4 shadow-sm">
              {selectedCol ? (
                <>
                  <div className="border-b border-slate-800 pb-3">
                    <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
                      Column Profile
                    </div>
                    <h3 className="text-base font-bold text-white font-mono mt-0.5">
                      {selectedCol.column_name}
                    </h3>
                  </div>

                  {/* Type distribution breakdown */}
                  <div>
                    <div className="text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1">
                      <Fingerprint className="w-3.5 h-3.5 text-indigo-400" /> Type Distribution
                    </div>
                    <div className="space-y-1.5 text-xs font-mono">
                      {Object.entries(selectedCol.inferred_types).map(([t, count]) => (
                        <div key={t} className="flex justify-between items-center bg-slate-800/60 px-2.5 py-1 rounded">
                          <span className="text-slate-300">{t}</span>
                          <span className="text-slate-400 font-semibold">
                            {count} ({Math.round((count / selectedCol.total_count) * 100)}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Anomalies Detected */}
                  <div className="space-y-2 pt-2 border-t border-slate-800 text-xs">
                    <div className="font-semibold text-slate-400">Anomalies Detected</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="bg-slate-800/40 p-2 rounded">
                        <div className="text-slate-500 text-[10px]">Whitespace Glitches</div>
                        <div className="font-mono font-bold text-slate-200">
                          {selectedCol.leading_trailing_whitespace_count}
                        </div>
                      </div>
                      <div className="bg-slate-800/40 p-2 rounded">
                        <div className="text-slate-500 text-[10px]">Case Inconsistencies</div>
                        <div className="font-mono font-bold text-slate-200">
                          {selectedCol.case_inconsistencies}
                        </div>
                      </div>
                      <div className="bg-slate-800/40 p-2 rounded">
                        <div className="text-slate-500 text-[10px]">IQR Outliers</div>
                        <div className="font-mono font-bold text-slate-200">
                          {selectedCol.iqr_outliers_count}
                        </div>
                      </div>
                      <div className="bg-slate-800/40 p-2 rounded">
                        <div className="text-slate-500 text-[10px]">MAD Outliers</div>
                        <div className="font-mono font-bold text-slate-200">
                          {selectedCol.mad_outliers_count}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Numeric Stats if applicable */}
                  {selectedCol.is_numeric && selectedCol.mean !== undefined && (
                    <div className="pt-2 border-t border-slate-800 text-xs space-y-1">
                      <div className="font-semibold text-slate-400">Numeric Summary</div>
                      <div className="grid grid-cols-2 gap-2 text-slate-300 font-mono text-[11px]">
                        <div>Min: {selectedCol.min_value?.toFixed(2)}</div>
                        <div>Max: {selectedCol.max_value?.toFixed(2)}</div>
                        <div>Mean: {selectedCol.mean?.toFixed(2)}</div>
                        <div>Median: {selectedCol.median?.toFixed(2)}</div>
                      </div>
                    </div>
                  )}

                  {/* Top Patterns */}
                  {selectedCol.pattern_signatures && selectedCol.pattern_signatures.length > 0 && (
                    <div className="pt-2 border-t border-slate-800 text-xs">
                      <div className="font-semibold text-slate-400 mb-1">Top Regex Patterns</div>
                      <div className="space-y-1 font-mono text-[11px]">
                        {selectedCol.pattern_signatures.slice(0, 3).map(([pat, c], i) => (
                          <div key={i} className="truncate bg-slate-800/40 px-2 py-1 rounded text-slate-300">
                            {pat} <span className="text-slate-500">({c})</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-slate-500 text-xs text-center py-8">Select a column to inspect</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
