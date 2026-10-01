import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
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
  Sparkles,
  Zap,
  ArrowRight,
  FileSpreadsheet,
  FileText,
  Binary,
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
  const [isDragOver, setIsDragOver] = useState(false);

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
    setUploadStage('Ingesting asset to Cloudinary (bgrvz383)...');

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

      // 2. Ingest into TITAN backend engine
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
    <div className="max-w-4xl mx-auto space-y-8 relative">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <span className="px-3 py-1 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider bg-neutral-900 text-neutral-300 border border-neutral-800">
            Enterprise Ingestion Pipeline
          </span>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight uppercase mt-1">
            Upload & Profile Dataset
          </h1>
          <p className="text-xs text-neutral-400 mt-1">
            Files are stored in Cloudinary, synced to Firebase Firestore, and secured by TITAN guardrails.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-neutral-300 text-xs font-mono">
            <Cloud className="w-3.5 h-3.5 text-neutral-400" />
            <span>Cloudinary: bgrvz383</span>
          </div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-neutral-300 text-xs font-mono">
            <Flame className="w-3.5 h-3.5 text-neutral-400" />
            <span>Firestore: titan-d57bf</span>
          </div>
        </div>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-2xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs flex items-center gap-3"
        >
          <AlertTriangle className="w-5 h-5 shrink-0 text-red-400" />
          <span>{error}</span>
        </motion.div>
      )}

      {/* Upload Guard Summary Banner if completed */}
      {uploadResult && uploadResult.dataset && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="p-7 rounded-3xl bg-neutral-950 border border-neutral-800 text-neutral-200 space-y-4 shadow-2xl"
        >
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">
                  Ingested & Guardrails Passed
                </h3>
                <p className="text-xs text-neutral-400">Canonical SHA-256 generated and verified.</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              {(cloudinaryUrl || uploadResult.dataset.cloudinary_url) && (
                <a
                  href={cloudinaryUrl || uploadResult.dataset.cloudinary_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 rounded-full bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 text-neutral-300 hover:text-white font-semibold text-xs flex items-center gap-1.5 transition-all"
                >
                  <Cloud className="w-3.5 h-3.5 text-neutral-400" />
                  <span>Cloudinary URL</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => navigate('/profile')}
                className="px-5 py-2 rounded-full bg-white text-black font-semibold text-xs transition-all cursor-pointer flex items-center gap-1.5 hover:bg-neutral-200 shadow-md"
              >
                <span>Inspect Profile</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </motion.button>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 pt-2 text-xs">
            <div className="bg-neutral-900/80 p-3.5 rounded-2xl border border-neutral-800">
              <div className="text-neutral-400 text-[10px] uppercase font-bold">Rows Ingested</div>
              <div className="font-extrabold text-white font-mono text-base mt-0.5">
                {uploadResult.dataset.rows.toLocaleString()}
              </div>
            </div>
            <div className="bg-neutral-900/80 p-3.5 rounded-2xl border border-neutral-800">
              <div className="text-neutral-400 text-[10px] uppercase font-bold">Null Bytes Stripped</div>
              <div className="font-extrabold text-white font-mono text-base mt-0.5">
                {uploadResult.null_bytes_stripped}
              </div>
            </div>
            <div className="bg-neutral-900/80 p-3.5 rounded-2xl border border-neutral-800">
              <div className="text-neutral-400 text-[10px] uppercase font-bold">Formula Injections</div>
              <div className="font-extrabold text-white font-mono text-base mt-0.5">
                {uploadResult.formula_injection_cells_detected} <span className="text-xs font-normal text-neutral-400">neutralized</span>
              </div>
            </div>
            <div className="bg-neutral-900/80 p-3.5 rounded-2xl border border-neutral-800">
              <div className="text-neutral-400 text-[10px] uppercase font-bold">Storage & DB</div>
              <div className="font-extrabold text-white font-mono text-xs mt-1 truncate">
                Cloudinary + Firestore
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Main Form & Drag/Drop Card */}
      <form onSubmit={handleUpload} className="space-y-6">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
              const dropped = e.dataTransfer.files[0];
              setFile(dropped);
              const ext = dropped.name.split('.').pop()?.toLowerCase();
              if (ext === 'json') setFormat('json');
              else if (ext === 'parquet') setFormat('parquet');
              else if (ext === 'xlsx' || ext === 'xls') setFormat('excel');
              else setFormat('csv');
            }
          }}
          className={`p-10 rounded-3xl border-2 border-dashed transition-all duration-300 relative flex flex-col items-center justify-center text-center cursor-pointer ${
            isDragOver
              ? 'border-white bg-neutral-900 scale-[1.01]'
              : file
              ? 'border-neutral-700 bg-neutral-950/80 shadow-xl'
              : 'border-neutral-800 bg-neutral-950 hover:border-neutral-700 hover:bg-neutral-900/40 shadow-xl'
          }`}
        >
          <input
            type="file"
            onChange={handleFileChange}
            accept=".csv,.xlsx,.xls,.tsv,.json,.parquet"
            className="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-10"
          />

          <div className="w-16 h-16 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white mb-4 shadow-inner">
            <UploadCloud className="w-8 h-8 text-neutral-300" />
          </div>

          {file ? (
            <div className="space-y-1 z-20">
              <div className="text-white font-semibold text-base flex items-center gap-2 justify-center">
                <span>{file.name}</span>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-neutral-900 text-neutral-200 border border-neutral-800">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              </div>
              <p className="text-xs text-neutral-400">Click or drag a new file to replace</p>
            </div>
          ) : (
            <div className="space-y-1.5">
              <div className="text-white font-semibold text-base tracking-tight">
                Drop your raw enterprise dataset here
              </div>
              <p className="text-xs text-neutral-400 max-w-sm mx-auto">
                Supports CSV, Excel (XLSX/XLS), JSON, TSV, and Parquet. Automatically vaulted in Cloudinary.
              </p>
            </div>
          )}

          {/* Format Badges */}
          <div className="flex items-center gap-2 mt-6 flex-wrap justify-center">
            {['CSV', 'Excel (XLSX)', 'JSON', 'Parquet', 'TSV'].map((f) => (
              <span
                key={f}
                className="px-3 py-1 rounded-full text-[11px] font-mono bg-neutral-900 text-neutral-400 border border-neutral-800"
              >
                {f}
              </span>
            ))}
          </div>
        </div>

        {/* Progress Bar during upload */}
        {uploading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-5 rounded-3xl bg-neutral-950 border border-neutral-800 space-y-2.5"
          >
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-white flex items-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {uploadStage}
              </span>
              <span className="font-mono text-white font-bold">{uploadProgress}%</span>
            </div>
            <div className="w-full h-2 bg-neutral-900 rounded-full overflow-hidden border border-neutral-800">
              <motion.div
                className="h-full bg-white"
                animate={{ width: `${uploadProgress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
          </motion.div>
        )}

        {/* Upload Action Button */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={!file || uploading}
            className="px-8 py-3 rounded-full bg-white text-black font-semibold text-xs flex items-center gap-2 hover:bg-neutral-200 transition-all shadow-md cursor-pointer disabled:opacity-50"
          >
            <Zap className="w-4 h-4 fill-black" />
            <span>{uploading ? 'Ingesting Dataset...' : 'Begin Ingestion & Profile'}</span>
          </motion.button>
        </div>
      </form>
    </div>
  );
};
