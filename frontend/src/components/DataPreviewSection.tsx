import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { apiRequest } from '../api/client';
import {
  Table,
  CheckCircle2,
  AlertCircle,
  Eye,
  Download,
  ArrowRight,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

interface DataPreviewSectionProps {
  runId: string;
  onOpenExport: () => void;
}

interface PreviewData {
  run_id: string;
  dataset_id: string;
  filename: string;
  input_format: string;
  recommended_format: string;
  download_filename: string;
  status: string;
  is_cleaned: boolean;
  total_rows: number;
  columns: string[];
  raw_sample: Record<string, any>[];
  current_sample: Record<string, any>[];
  sample_mutations_count: number;
}

export const DataPreviewSection: React.FC<DataPreviewSectionProps> = ({ runId, onOpenExport }) => {
  const [data, setData] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'clean' | 'raw' | 'diff'>('clean');

  const fetchPreview = async () => {
    try {
      setLoading(true);
      const res = await apiRequest<PreviewData>(`/api/runs/${runId}/data-preview?limit=15`);
      setData(res);
    } catch (err) {
      console.error('Failed to load data preview:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (runId) {
      fetchPreview();
    }
  }, [runId]);

  if (loading) {
    return (
      <div className="rounded-3xl bg-neutral-950 border border-neutral-800 p-12 text-center text-neutral-400 text-xs flex flex-col items-center justify-center gap-2.5">
        <RefreshCw className="w-5 h-5 animate-spin text-white" />
        <span>Loading high-fidelity data reconciliation...</span>
      </div>
    );
  }

  if (!data || data.columns.length === 0) {
    return null;
  }

  const sampleRows = viewMode === 'raw' ? data.raw_sample : data.current_sample;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-3xl bg-neutral-950 border border-neutral-800/90 overflow-hidden shadow-2xl"
    >
      {/* Top Header */}
      <div className="p-6 border-b border-neutral-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-neutral-900/60">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-white shrink-0">
            <Table className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h3 className="text-sm font-semibold text-white tracking-tight uppercase">
                Live Data Inspection & Diff Reconciliation
              </h3>
              {data.is_cleaned ? (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-white/10 text-white border border-white/20 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-white" /> CLEANED & CORRECTED
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-neutral-900 text-neutral-300 border border-neutral-800">
                  RAW UNMODIFIED
                </span>
              )}
            </div>
            <p className="text-xs text-neutral-400 mt-1 font-sans">
              Showing preview rows. <span className="text-white font-semibold">{data.sample_mutations_count}</span> cell modifications verified by ledger engine.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-neutral-900 p-1 rounded-full border border-neutral-800 text-xs">
            <button
              onClick={() => setViewMode('clean')}
              className={`px-3.5 py-1 rounded-full font-medium text-xs transition-all cursor-pointer ${
                viewMode === 'clean'
                  ? 'bg-neutral-800 text-white shadow-sm'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              Correct Data
            </button>
            <button
              onClick={() => setViewMode('raw')}
              className={`px-3.5 py-1 rounded-full font-medium text-xs transition-all cursor-pointer ${
                viewMode === 'raw'
                  ? 'bg-neutral-800 text-white shadow-sm'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              Raw Input
            </button>
            <button
              onClick={() => setViewMode('diff')}
              className={`px-3.5 py-1 rounded-full font-medium text-xs transition-all cursor-pointer ${
                viewMode === 'diff'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              Diff View
            </button>
          </div>

          {/* Download Clean Button */}
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={onOpenExport}
            className="px-5 py-2 rounded-full bg-white text-black font-semibold text-xs flex items-center gap-1.5 hover:bg-neutral-200 shadow-md transition-all cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-black" />
            <span>Download ({data.recommended_format.toUpperCase()})</span>
          </motion.button>
        </div>
      </div>

      {/* Tabular Preview */}
      <div className="overflow-x-auto max-h-[380px]">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-neutral-900/90 sticky top-0 text-neutral-400 uppercase tracking-wider font-semibold text-[10px] border-b border-neutral-800 z-10 backdrop-blur-md">
            <tr>
              <th className="py-3.5 px-4 font-mono w-12 text-neutral-500">#</th>
              {data.columns.map((col) => (
                <th key={col} className="py-3.5 px-4 text-neutral-300 font-mono text-[11px] whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-850 text-neutral-200 font-mono text-[11px]">
            {viewMode === 'diff' ? (
              // Diff View showing raw vs corrected side by side
              data.raw_sample.map((rawRow, rIdx) => {
                const cleanRow = data.current_sample[rIdx] || {};
                return (
                  <tr key={rIdx} className="hover:bg-neutral-900/40 transition-colors">
                    <td className="py-3 px-4 text-neutral-500">{rIdx + 1}</td>
                    {data.columns.map((col) => {
                      const rawVal = String(rawRow[col] ?? '');
                      const cleanVal = String(cleanRow[col] ?? '');
                      const isChanged = rawVal !== cleanVal;

                      return (
                        <td
                          key={col}
                          className={`py-3 px-4 whitespace-nowrap ${
                            isChanged ? 'bg-amber-950/20 border-l-2 border-l-amber-500/50' : ''
                          }`}
                        >
                          {isChanged ? (
                            <div className="space-y-0.5">
                              <div className="text-red-400/80 line-through text-[10px]">
                                {rawVal || '<empty>'}
                              </div>
                              <div className="text-white font-semibold flex items-center gap-1">
                                <span>{cleanVal || '<empty>'}</span>
                                <Sparkles className="w-2.5 h-2.5 text-white inline" />
                              </div>
                            </div>
                          ) : (
                            <span className="text-neutral-300">{cleanVal}</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            ) : (
              // Standard View (Cleaned or Raw)
              sampleRows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-neutral-900/40 transition-colors">
                  <td className="py-3 px-4 text-neutral-500">{rIdx + 1}</td>
                  {data.columns.map((col) => {
                    const rawVal = String(data.raw_sample[rIdx]?.[col] ?? '');
                    const currentVal = String(row[col] ?? '');
                    const isMutated = viewMode === 'clean' && data.is_cleaned && rawVal !== currentVal;

                    return (
                      <td
                        key={col}
                        className={`py-3 px-4 whitespace-nowrap ${
                          isMutated ? 'bg-white/10 text-white font-medium' : 'text-neutral-300'
                        }`}
                      >
                        {currentVal}
                        {isMutated && (
                          <span className="ml-1.5 px-2 py-0.2 rounded-full text-[9px] bg-white/10 text-white font-medium border border-white/20">
                            cleaned
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer notice */}
      <div className="px-6 py-3.5 bg-neutral-950 border-t border-neutral-800 text-xs text-neutral-400 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <span>
          Showing top {sampleRows.length} sample records of {data.total_rows.toLocaleString()} total rows in dataset.
        </span>
        <button
          onClick={onOpenExport}
          className="text-white hover:text-neutral-200 font-medium inline-flex items-center gap-1.5 text-xs transition-colors cursor-pointer group"
        >
          <span>Export full dataset in {data.input_format.toUpperCase()}</span>
          <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </motion.div>
  );
};
