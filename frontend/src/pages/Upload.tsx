import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { Dataset, UploadGuardResponse } from '../types';
import { uploadToCloudinary } from '../utils/cloudinary';
import { syncDatasetToFirestore, logAuditToFirestore } from '../firebase/config';
import {
  UploadCloud,
  FileCode,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Cloud,
  Flame,
} from 'lucide-react';

interface UploadProps {
  onDatasetLoaded: (dataset: Dataset) => void;
}

export const Upload: React.FC<UploadProps> = ({ onDatasetLoaded }) => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [format, setFormat] = useState('csv');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState<string>('');
  const [uploadResult, setUploadResult] = useState<UploadGuardResponse | null>(null);
  const [cloudinaryUrl, setCloudinaryUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
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
    setCloudinaryUrl(null);
    setUploadProgress(15);
    setUploadStage('Uploading to Cloudinary (bgrvz383)...');

    try {
      // 1. Upload to Cloudinary directly with preset TITAN-project
      let cloudUrl = '';
      try {
        const cloudRes = await uploadToCloudinary(file, (percent) => {
          setUploadProgress(Math.min(50, Math.round(percent / 2)));
        });
        cloudUrl = cloudRes.secure_url;
        setCloudinaryUrl(cloudUrl);
        setUploadProgress(60);
      } catch (cloudErr: any) {
        console.warn('Cloudinary direct upload note:', cloudErr.message);
      }

      // 2. Ingest into CleanSlate backend engine
      setUploadStage('Running Guardrails & SHA-256 Hash Verification...');
      setUploadProgress(75);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('format', format);

      const res = await apiRequest<UploadGuardResponse>('/api/datasets/upload', {
        method: 'POST',
        body: formData,
      });

      if (cloudUrl && res.dataset) {
        res.dataset.cloudinary_url = cloudUrl;
      }

      setUploadResult(res);
      setUploadProgress(90);

      // 3. Sync to Firebase Firestore
      if (res.dataset) {
        setUploadStage('Syncing metadata to Firebase Firestore (titan-d57bf)...');
        await syncDatasetToFirestore({
          id: res.dataset.id,
          filename: res.dataset.filename,
          rows: res.dataset.rows,
          cols: res.dataset.cols,
          format: res.dataset.format,
          canonical_hash: res.dataset.canonical_hash,
          cloudinary_url: cloudUrl || res.dataset.cloudinary_url,
          created_at: res.dataset.created_at,
        });

        await logAuditToFirestore({
          actor: 'current_user',
          event: 'DATASET_UPLOAD_SUCCESS',
          dataset_id: res.dataset.id,
          details: {
            filename: file.name,
            rows: res.dataset.rows,
            cloudinary: cloudUrl || 'active',
          },
          timestamp: new Date().toISOString(),
        });

        onDatasetLoaded(res.dataset);
      }
      setUploadProgress(100);
      setUploadStage('Completed successfully!');
    } catch (err: any) {
      setError(err.message || 'File upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Upload Dataset</h1>
          <p className="text-xs text-slate-400 mt-1">
            Files are stored in Cloudinary, synced to Firebase Firestore, and secured by CleanSlate.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 text-[11px] font-medium">
            <Cloud className="w-3.5 h-3.5" />
            <span>Cloudinary: bgrvz383</span>
          </div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[11px] font-medium">
            <Flame className="w-3.5 h-3.5" />
            <span>Firestore: titan-d57bf</span>
          </div>
        </div>
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
            <div className="flex items-center gap-2">
              {(cloudinaryUrl || uploadResult.dataset.cloudinary_url) && (
                <a
                  href={cloudinaryUrl || uploadResult.dataset.cloudinary_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs flex items-center gap-1.5 transition-colors"
                >
                  <Cloud className="w-3.5 h-3.5" />
                  <span>Cloudinary URL</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
              <button
                onClick={() => navigate('/profile')}
                className="px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold text-xs hover:bg-emerald-400 transition-colors"
              >
                Inspect Profile →
              </button>
            </div>
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
              <div className="text-slate-400">Storage & DB</div>
              <div className="font-bold text-cyan-400 font-mono text-xs truncate">Cloudinary + Firestore</div>
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
              : 'CSV, JSON Lines, Parquet, or Excel format'}
          </p>
        </div>

        {uploading && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-slate-400">
              <span>{uploadStage}</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 via-sky-500 to-emerald-500 transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </div>
        )}

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
              Storage & Database
            </label>
            <div className="flex items-center gap-2 h-9 px-3 bg-slate-800/60 border border-slate-700/60 rounded-lg text-xs text-emerald-400 font-mono">
              <ShieldCheck className="w-4 h-4" />
              <span>Cloudinary (bgrvz383) + Firestore Live</span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end pt-4 border-t border-slate-800">
          <button
            type="submit"
            disabled={!file || uploading}
            className="px-6 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 flex items-center gap-2"
          >
            <FileCode className="w-4 h-4" />
            {uploading ? 'Uploading to Cloudinary & Securing...' : 'Upload & Clean Dataset'}
          </button>
        </div>
      </form>
    </div>
  );
};
