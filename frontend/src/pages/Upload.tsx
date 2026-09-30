import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { Dataset, UploadGuardResponse } from '../types';
import {
  UploadCloud,
  FileCode,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

interface UploadProps {
  onDatasetLoaded: (dataset: Dataset) => void;
}

export const Upload: React.FC<UploadProps> = ({ onDatasetLoaded }) => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [format, setFormat] = useState('csv');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadGuardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingDemo, setLoadingDemo] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      // Auto detect format from extension
      const ext = selected.name.split('.').pop()?.toLowerCase();
      if (ext === 'json') setFormat('json');
      else if (ext === 'parquet') setFormat('parquet');
      else if (ext === 'xlsx' || ext === 'xls') setFormat('excel');
      else setFormat('csv');
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('format', format);

    try {
      const res = await apiRequest<UploadGuardResponse>('/api/datasets/upload', {
        method: 'POST',
        body: formData,
      });
      setUploadResult(res);
      if (res.dataset) {
        onDatasetLoaded(res.dataset);
      }
    } catch (err: any) {
      setError(err.message || 'File upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleLoadDemo = async () => {
    setLoadingDemo(true);
    setError(null);
    try {
      const res = await apiRequest<{ dataset: Dataset }>('/api/datasets/demo', { method: 'POST' });
      onDatasetLoaded(res.dataset);
      navigate('/profile');
    } catch (err: any) {
      setError(err.message || 'Demo synthesis failed');
    } finally {
      setLoadingDemo(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">Upload Enterprise Dataset</h1>
        <p className="text-xs text-slate-400 mt-1">
          Supports CSV, JSON, Parquet, and Excel formats. Upload Guard runs adversarial checks, strips formula injections, and calculates canonical SHA-256 hash.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Guard Summary Banner if completed */}
      {uploadResult && uploadResult.dataset && (
        <div className="p-5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
              <CheckCircle2 className="w-5 h-5" />
              <span>Ingested & Secured Successfully</span>
            </div>
            <button
              onClick={() => navigate('/profile')}
              className="px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold text-xs hover:bg-emerald-400 transition-colors"
            >
              Inspect Profile →
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 text-xs">
            <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
              <div className="text-slate-400">Rows Ingested</div>
              <div className="font-bold text-white font-mono text-sm">{uploadResult.dataset.rows.toLocaleString()}</div>
            </div>
            <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
              <div className="text-slate-400">Null Bytes Stripped</div>
              <div className="font-bold text-emerald-400 font-mono text-sm">{uploadResult.null_bytes_stripped}</div>
            </div>
            <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
              <div className="text-slate-400">Formula Injections</div>
              <div className="font-bold text-amber-400 font-mono text-sm">{uploadResult.formula_injection_cells_detected} neutralized</div>
            </div>
            <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
              <div className="text-slate-400">Quarantine Rows</div>
              <div className="font-bold text-cyan-400 font-mono text-sm">{uploadResult.quarantined_count}</div>
            </div>
          </div>
        </div>
      )}

      {/* Main Upload Form */}
      <form onSubmit={handleUpload} className="p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-6">
        <div className="border-2 border-dashed border-slate-700/80 hover:border-indigo-500/60 rounded-xl p-8 text-center transition-colors relative">
          <input
            type="file"
            onChange={handleFileChange}
            accept=".csv,.tsv,.json,.parquet,.xlsx,.xls"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          <UploadCloud className="w-12 h-12 text-indigo-400 mx-auto mb-3" />
          <p className="text-sm font-semibold text-white">
            {file ? file.name : 'Click to select or drag and drop dataset file'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {file
              ? `${(file.size / 1024).toFixed(1)} KB selected`
              : 'CSV, JSON Lines, Parquet, or Excel (up to 50MB)'}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Data Format
            </label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="csv">CSV (Auto-detect comma, semicolon, tab)</option>
              <option value="json">JSON / JSON-Lines</option>
              <option value="parquet">Apache Parquet</option>
              <option value="excel">Microsoft Excel (.xlsx)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Upload Guard Level
            </label>
            <div className="flex items-center gap-2 h-9 px-3 bg-slate-800/60 border border-slate-700/60 rounded-lg text-xs text-emerald-400 font-mono">
              <ShieldCheck className="w-4 h-4" />
              <span>Full Adversarial Defense Active</span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={handleLoadDemo}
            disabled={loadingDemo}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-medium border border-slate-700 flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <Sparkles className={`w-3.5 h-3.5 ${loadingDemo ? 'animate-spin' : ''}`} />
            {loadingDemo ? 'Synthesizing...' : 'Or Load 500-Row Enterprise Messy Demo'}
          </button>

          <button
            type="submit"
            disabled={!file || uploading}
            className="px-6 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 flex items-center gap-2"
          >
            <FileCode className="w-4 h-4" />
            {uploading ? 'Processing Guard & Hash...' : 'Ingest & Secure Dataset'}
          </button>
        </div>
      </form>
    </div>
  );
};
