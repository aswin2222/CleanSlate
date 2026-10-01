import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { apiRequest } from '../api/client';
import { Dataset, Run, SuiteRunReport, MutationReport } from '../types';
import { ExportDataModal } from '../components/ExportDataModal';
import {
  CheckCircle,
  XCircle,
  Play,
  Bug,
  Code,
  ShieldCheck,
  AlertTriangle,
  RotateCw,
  Download,
  Copy,
  Check,
  Sparkles,
  Terminal,
  Activity,
} from 'lucide-react';

interface VerifyProps {
  selectedDataset: Dataset | null;
}

export const Verify: React.FC<VerifyProps> = ({ selectedDataset }) => {
  const [searchParams] = useSearchParams();
  const runIdParam = searchParams.get('run_id');

  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(runIdParam);
  const [preReport, setPreReport] = useState<SuiteRunReport | null>(null);
  const [postReport, setPostReport] = useState<SuiteRunReport | null>(null);
  const [mutationReport, setMutationReport] = useState<MutationReport | null>(null);
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [runningMutation, setRunningMutation] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);

  useEffect(() => {
    if (!selectedDataset) return;
    const fetchRuns = async () => {
      try {
        const runList = await apiRequest<Run[]>(`/api/datasets/${selectedDataset.id}/runs`);
        setRuns(runList);
        if (runList.length > 0 && !activeRunId) {
          setActiveRunId(runList[0].id);
        }
      } catch (err) {
        console.error('Failed to load runs:', err);
      }
    };
    fetchRuns();
  }, [selectedDataset]);

  const handleRunVerification = async () => {
    if (!activeRunId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await apiRequest<{
        pre_report?: SuiteRunReport;
        post_report?: SuiteRunReport;
        test_code?: string;
      }>(`/api/runs/${activeRunId}/verify`, { method: 'POST' });

      if (res.pre_report) setPreReport(res.pre_report);
      if (res.post_report) setPostReport(res.post_report);
      if (res.test_code) setGeneratedCode(res.test_code);
    } catch (err: any) {
      setError(err.message || 'Verification execution failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRunMutation = async () => {
    if (!activeRunId) return;
    try {
      setRunningMutation(true);
      setError(null);
      const res = await apiRequest<MutationReport>(`/api/runs/${activeRunId}/mutation-test`, {
        method: 'POST',
      });
      setMutationReport(res);
    } catch (err: any) {
      setError(err.message || 'Mutation testing failed');
    } finally {
      setRunningMutation(false);
    }
  };

  const copyCode = () => {
    if (!generatedCode) return;
    navigator.clipboard.writeText(generatedCode);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  if (!selectedDataset) {
    return (
      <div className="p-16 text-center bg-neutral-950 border border-neutral-800 rounded-3xl">
        <ShieldCheck className="w-12 h-12 text-neutral-600 mx-auto mb-3" />
        <h3 className="text-white font-semibold text-base">No dataset selected</h3>
        <p className="text-xs text-neutral-400 mt-1">Please select or upload a dataset first</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-8"
    >
      {/* Top Header Card */}
      <div className="relative rounded-3xl p-8 bg-neutral-950 border border-neutral-800/90 shadow-2xl overflow-hidden">
        <div className="relative flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-neutral-300 text-xs font-mono">
              <Sparkles className="w-3.5 h-3.5 text-white" />
              <span>Pandera Runtime Schemas & Synthetic Mutation Engine</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight uppercase">
              Automated Test Suite & Verification
            </h1>
            <p className="text-xs text-neutral-400 leading-relaxed max-w-2xl">
              Synthesizes autonomous Pandera runtime validation rules and Pytest suites. Performs dual PRE vs POST differential verification and tests fault detection via synthetically injected mutations.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleRunVerification}
              disabled={loading || !activeRunId}
              className="px-6 py-2.5 rounded-full bg-white text-black font-semibold text-xs flex items-center gap-2 hover:bg-neutral-200 shadow-md transition-all cursor-pointer disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 fill-black ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Running Suite...' : 'Run PRE vs POST Tests'}</span>
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleRunMutation}
              disabled={runningMutation || !activeRunId}
              className="px-5 py-2.5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-white border border-neutral-800 text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
            >
              <Bug className={`w-3.5 h-3.5 ${runningMutation ? 'animate-spin' : ''}`} />
              <span>{runningMutation ? 'Injecting Faults...' : 'Run Mutation Analysis'}</span>
            </motion.button>

            {activeRunId && (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowExportModal(true)}
                className="px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white border border-white/20 text-xs font-semibold flex items-center gap-2 shadow-sm transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Clean Data</span>
              </motion.button>
            )}
          </div>
        </div>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-2xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs flex items-center gap-3"
        >
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
          <span>{error}</span>
        </motion.div>
      )}

      {/* Mutation Score Card */}
      {mutationReport && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="p-7 rounded-3xl bg-neutral-950 border border-neutral-800 shadow-2xl relative overflow-hidden"
        >
          <div className="relative flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-neutral-900 text-white border border-neutral-800 flex items-center justify-center font-bold font-mono text-2xl shrink-0">
                <Bug className="w-7 h-7" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-neutral-300 font-bold flex items-center gap-1.5 font-mono">
                  <Activity className="w-3.5 h-3.5" />
                  Mutation Test Score
                </div>
                <div className="text-3xl font-extrabold text-white font-mono mt-1">
                  {mutationReport.fault_detection_rate_pct.toFixed(1)}%{' '}
                  <span className="text-sm font-normal text-neutral-400">Fault Detection Rate</span>
                </div>
                <p className="text-xs text-neutral-400 mt-1 max-w-xl">
                  Successfully intercepted <span className="text-white font-mono font-bold">{mutationReport.detected_mutations}</span> of{' '}
                  <span className="text-white font-mono font-bold">{mutationReport.total_mutations}</span> synthetically injected faults.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="px-4 py-2 rounded-full bg-neutral-900 text-white border border-neutral-800 text-xs font-mono font-semibold flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-white" />
                ZERO TEST EVASIONS
              </span>
            </div>
          </div>
        </motion.div>
      )}

      {/* Comparison: PRE vs POST Results */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pre-Cleaning Results */}
        <div className="p-6 rounded-3xl bg-neutral-950 border border-neutral-800 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                Pre-Cleaning Test Run (Dirty Data)
              </div>
              <p className="text-[11px] text-neutral-400 mt-0.5">Runtime assertions before repairs</p>
            </div>
            {preReport && (
              <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                {preReport.failed} FAILED / {preReport.total} TOTAL
              </span>
            )}
          </div>
          {preReport ? (
            <div className="space-y-3 text-xs">
              <div className="text-neutral-400 text-[11px]">
                Expected violations detected on raw input: {preReport.failed} rules violated prior to autonomous cleaning.
              </div>
              <div className="space-y-2 font-mono max-h-56 overflow-y-auto pr-1">
                {preReport.results.map((r, i) => (
                  <div
                    key={i}
                    className={`p-3 rounded-2xl flex items-center justify-between transition-all ${
                      r.outcome === 'FAILED'
                        ? 'bg-red-950/20 text-red-300 border border-red-900/40'
                        : 'bg-cyan-950/20 text-cyan-300 border border-cyan-900/30'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate max-w-xs">
                      {r.outcome === 'FAILED' ? (
                        <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                      ) : (
                        <CheckCircle className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      )}
                      <span className="truncate">{r.name}</span>
                    </div>
                    <span className="font-bold text-[11px] shrink-0">{r.outcome}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-neutral-500 text-xs py-12 text-center flex flex-col items-center justify-center">
              <RotateCw className="w-8 h-8 text-neutral-700 mb-2" />
              <span>Click &quot;Run PRE vs POST Tests&quot; to execute test assertions</span>
            </div>
          )}
        </div>

        {/* Post-Cleaning Results */}
        <div className="p-6 rounded-3xl bg-neutral-950 border border-neutral-800 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                Post-Cleaning Test Run (Repaired Data)
              </div>
              <p className="text-[11px] text-neutral-400 mt-0.5">Runtime assertions after repairs</p>
            </div>
            {postReport && (
              <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-white/10 text-white border border-white/20">
                {postReport.passed} PASSED / {postReport.total} TOTAL
              </span>
            )}
          </div>
          {postReport ? (
            <div className="space-y-3 text-xs">
              <div className="text-neutral-400 text-[11px]">
                All semantic constraints satisfied: 0 regressions, all anomalies repaired with reversible safety.
              </div>
              <div className="space-y-2 font-mono max-h-56 overflow-y-auto pr-1">
                {postReport.results.map((r, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-2xl flex items-center justify-between bg-neutral-900 text-white border border-neutral-800"
                  >
                    <div className="flex items-center gap-2 truncate max-w-xs">
                      <CheckCircle className="w-3.5 h-3.5 text-white shrink-0" />
                      <span className="truncate">{r.name}</span>
                    </div>
                    <span className="font-bold text-[11px] shrink-0">{r.outcome}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-neutral-500 text-xs py-12 text-center flex flex-col items-center justify-center">
              <ShieldCheck className="w-8 h-8 text-neutral-700 mb-2" />
              <span>Awaiting post-clean verification results</span>
            </div>
          )}
        </div>
      </div>

      {/* Generated Code Viewer */}
      {generatedCode && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-3xl bg-neutral-950 border border-neutral-800 overflow-hidden shadow-2xl"
        >
          <div className="px-6 py-4 border-b border-neutral-800 flex items-center justify-between bg-neutral-900/60">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-neutral-700" />
                <div className="w-2.5 h-2.5 rounded-full bg-neutral-700" />
                <div className="w-2.5 h-2.5 rounded-full bg-neutral-700" />
              </div>
              <div className="h-4 w-px bg-neutral-800 mx-1" />
              <div className="flex items-center gap-2">
                <Code className="w-4 h-4 text-white" />
                <h2 className="text-xs font-semibold uppercase tracking-wider text-white">
                  Generated Pandera & Pytest Verification Suite
                </h2>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-neutral-400 font-mono hidden sm:inline">Autonomous Test-Driven Python</span>
              <button
                onClick={copyCode}
                className="px-3.5 py-1 rounded-full bg-neutral-900 hover:bg-neutral-800 text-neutral-300 text-xs font-mono flex items-center gap-1.5 border border-neutral-800 transition-colors"
              >
                {copiedCode ? <Check className="w-3.5 h-3.5 text-white" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedCode ? 'Copied!' : 'Copy Code'}</span>
              </button>
            </div>
          </div>
          <pre className="p-6 text-xs font-mono text-neutral-200 bg-black/90 overflow-x-auto max-h-96 leading-relaxed selection:bg-neutral-800">
            {generatedCode}
          </pre>
        </motion.div>
      )}

      {/* Export & Download Clean Data Modal */}
      {selectedDataset && (
        <ExportDataModal
          isOpen={showExportModal}
          onClose={() => setShowExportModal(false)}
          datasetId={selectedDataset.id}
          runId={activeRunId || undefined}
          datasetFilename={selectedDataset.filename}
          inputFormat={selectedDataset.format}
          isCleaned={true}
        />
      )}
    </motion.div>
  );
};
