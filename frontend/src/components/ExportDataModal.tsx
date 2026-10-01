import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { downloadFile } from '../api/client';
import {
  Download,
  FileSpreadsheet,
  FileText,
  FileCode,
  Layers,
  CheckCircle2,
  X,
  Sparkles,
  ShieldCheck,
  Table,
  Binary,
} from 'lucide-react';

interface ExportDataModalProps {
  isOpen: boolean;
  onClose: () => void;
  datasetId?: string;
  runId?: string;
  datasetFilename: string;
  inputFormat: string;
  isCleaned?: boolean;
}

interface FormatOption {
  id: string;
  label: string;
  ext: string;
  desc: string;
  icon: React.ReactNode;
  recommended?: boolean;
}

export const ExportDataModal: React.FC<ExportDataModalProps> = ({
  isOpen,
  onClose,
  datasetId,
  runId,
  datasetFilename,
  inputFormat,
  isCleaned = true,
}) => {
  const normInputFormat = (inputFormat || 'csv').toLowerCase().replace('.', '');
  const [selectedFormat, setSelectedFormat] = useState<string>('auto');
  const [downloading, setDownloading] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const formats: FormatOption[] = [
    {
      id: 'auto',
      label: `Same as Input (${normInputFormat.toUpperCase()})`,
      ext: `.${normInputFormat}`,
      desc: `Guarantees identical output structure matching your original uploaded ${normInputFormat.toUpperCase()} file`,
      icon: <Sparkles className="w-5 h-5 text-white" />,
      recommended: true,
    },
    {
      id: 'csv',
      label: 'CSV (Comma-Separated)',
      ext: '.csv',
      desc: 'Standard CSV with formula injection neutralization (=, +, -, @ escaped)',
      icon: <FileText className="w-5 h-5 text-neutral-300" />,
    },
    {
      id: 'xlsx',
      label: 'Excel Workbook',
      ext: '.xlsx',
      desc: 'Native Microsoft Excel spreadsheet with formula defense applied',
      icon: <FileSpreadsheet className="w-5 h-5 text-neutral-300" />,
    },
    {
      id: 'json',
      label: 'JSON Array',
      ext: '.json',
      desc: 'Formatted JSON array of record objects for APIs and modern databases',
      icon: <FileCode className="w-5 h-5 text-neutral-300" />,
    },
    {
      id: 'tsv',
      label: 'TSV (Tab-Separated)',
      ext: '.tsv',
      desc: 'Tab-delimited text format for data pipelines and statistical packages',
      icon: <Table className="w-5 h-5 text-neutral-300" />,
    },
    {
      id: 'jsonl',
      label: 'JSON Lines (NDJSON)',
      ext: '.jsonl',
      desc: 'One JSON object per line, ideal for big data streaming and LLM training',
      icon: <FileCode className="w-5 h-5 text-neutral-300" />,
    },
    {
      id: 'parquet',
      label: 'Apache Parquet',
      ext: '.parquet',
      desc: 'Columnar storage format for high-speed analytical engines and data lakes',
      icon: <Binary className="w-5 h-5 text-neutral-300" />,
    },
  ];

  const handleDownload = async () => {
    try {
      setDownloading(true);
      setError(null);
      setDownloadSuccess(false);

      const endpoint = runId
        ? `/api/runs/${runId}/export?format=${selectedFormat}`
        : `/api/datasets/${datasetId}/export?format=${selectedFormat}`;

      const ext =
        selectedFormat === 'auto'
          ? `.${normInputFormat}`
          : `.${selectedFormat}`;
      const rawStem = datasetFilename.replace(/\.[^/.]+$/, '');
      const cleanStem = rawStem.startsWith('clean') ? rawStem : `cleaned_${rawStem}`;
      const fallback = `${cleanStem}${ext}`;

      await downloadFile(endpoint, fallback);
      setDownloadSuccess(true);
      setTimeout(() => {
        setDownloadSuccess(false);
      }, 4000);
    } catch (err: any) {
      setError(err.message || 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/85 backdrop-blur-md"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94, y: 15 }}
          transition={{ type: 'spring', stiffness: 350, damping: 28 }}
          className="relative w-full max-w-2xl bg-neutral-950 border border-neutral-800 rounded-3xl shadow-[0_25px_70px_rgba(0,0,0,0.9)] p-6 sm:p-8 overflow-hidden z-10 text-white font-sans"
        >
          {/* Ambient Glows */}
          <div className="pointer-events-none absolute -top-20 -right-20 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl" />
          <div className="pointer-events-none absolute -bottom-20 -left-20 w-60 h-60 bg-teal-500/10 rounded-full blur-3xl" />

          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-neutral-800/80 relative z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-white">
                <Download className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
                  Download Cleaned Dataset
                  {isCleaned && (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-white/10 text-white border border-white/20">
                      100% REVERSIBLE
                    </span>
                  )}
                </h2>
                <p className="text-xs text-neutral-400 mt-0.5">
                  Target: <span className="font-mono text-white font-medium">{datasetFilename}</span> (Input: {normInputFormat.toUpperCase()})
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-full text-neutral-400 hover:text-white hover:bg-neutral-800/80 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Security / Defense Notice */}
          <div className="mt-4 p-3.5 rounded-2xl bg-neutral-900 border border-neutral-800 flex items-center gap-3 text-xs text-neutral-300 relative z-10 font-sans">
            <ShieldCheck className="w-5 h-5 text-white shrink-0" />
            <span>
              Cleaned dataset is formatted with <strong>formula injection defense</strong> (=, +, -, @ sanitized) and excludes internal metadata fields.
            </span>
          </div>

          {/* Format Selector Grid */}
          <div className="mt-5 space-y-2 max-h-[290px] overflow-y-auto pr-1 relative z-10">
            <label className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider block mb-2 font-mono">
              Select Output Format
            </label>
            {formats.map((fmt) => {
              const isSelected = selectedFormat === fmt.id;
              return (
                <div
                  key={fmt.id}
                  onClick={() => setSelectedFormat(fmt.id)}
                  className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                    isSelected
                      ? 'bg-neutral-900 border-white text-white shadow-sm'
                      : 'bg-neutral-900/40 border-neutral-800 hover:bg-neutral-900/80 hover:border-neutral-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="shrink-0">{fmt.icon}</div>
                    <div>
                      <div className="text-xs font-semibold text-white flex items-center gap-2">
                        <span>{fmt.label}</span>
                        {fmt.recommended && (
                          <span className="px-2 py-0.2 rounded-full text-[9px] font-mono font-bold bg-white/10 text-white border border-white/20 uppercase">
                            Exact Input Match
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-neutral-400 mt-0.5">{fmt.desc}</p>
                    </div>
                  </div>
                  <div className="shrink-0">
                    <span
                      className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                        isSelected
                          ? 'border-white bg-white text-black'
                          : 'border-neutral-700 bg-neutral-900'
                      }`}
                    >
                      {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-black" />}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {error && (
            <div className="mt-4 p-3 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs">
              {error}
            </div>
          )}

          {downloadSuccess && (
            <div className="mt-4 p-3 rounded-xl bg-neutral-900 border border-neutral-700 text-white text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-white" />
              <span>Clean dataset downloaded successfully to your machine!</span>
            </div>
          )}

          {/* Action Footer */}
          <div className="mt-6 pt-4 border-t border-neutral-800/80 flex items-center justify-between gap-4 relative z-10">
            <button
              onClick={onClose}
              className="px-5 py-2.5 rounded-full text-xs text-neutral-400 hover:text-white hover:bg-neutral-900 transition-colors cursor-pointer"
            >
              Cancel
            </button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleDownload}
              disabled={downloading}
              className="px-6 py-2.5 rounded-full bg-white text-black font-semibold text-xs flex items-center gap-2 hover:bg-neutral-200 transition-all shadow-md cursor-pointer disabled:opacity-50"
            >
              <Download className={`w-4 h-4 text-black ${downloading ? 'animate-bounce' : ''}`} />
              <span>{downloading ? 'Exporting File...' : 'Download File Now'}</span>
            </motion.button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
