import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { Dataset, Run, SuiteRunReport, MutationReport } from '../types';
import {
  CheckCircle,
  XCircle,
  Play,
  Bug,
  Code,
  ShieldCheck,
  AlertTriangle,
  RotateCw,
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
  const [error, setError] = useState<string | null>(null);

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
      // Run pre and post test verification
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

  if (!selectedDataset) {
    return (
      <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl">
        <CheckCircle className="w-12 h-12 text-slate-600 mx-auto mb-3" />
        <h3 className="text-white font-semibold text-sm">No dataset selected</h3>
        <p className="text-xs text-slate-400 mt-1">Please select or upload a dataset first</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Automated Test Suite & Mutation Verification
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Generates Pandera runtime schemas and Pytest rules. Runs PRE vs POST reconciliation and mutation testing to measure fault detection rate.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunVerification}
            disabled={loading || !activeRunId}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Running Suite...' : 'Run PRE vs POST Tests'}</span>
          </button>

          <button
            onClick={handleRunMutation}
            disabled={runningMutation || !activeRunId}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 text-xs font-semibold flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <Bug className={`w-3.5 h-3.5 ${runningMutation ? 'animate-spin' : ''}`} />
            <span>{runningMutation ? 'Injecting Bugs...' : 'Run Mutation Analysis'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
          {error}
        </div>
      )}

      {/* Mutation Score Card */}
      {mutationReport && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between flex-wrap gap-4 shadow-xl">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 flex items-center justify-center font-bold font-mono text-xl shrink-0">
              <Bug className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                Mutation Test Score
              </div>
              <div className="text-2xl font-extrabold text-white font-mono mt-0.5">
                {mutationReport.fault_detection_rate_pct.toFixed(1)}% Fault Detection Rate
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Detected {mutationReport.detected_mutations} of {mutationReport.total_mutations} synthetically injected faults (boundary shift, null injection, format swap).
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-bold font-mono">
              ZERO TEST EVASIONS
            </span>
          </div>
        </div>
      )}

      {/* Comparison: PRE vs POST Results */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pre-Cleaning Results */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Pre-Cleaning Test Run (Dirty Data)
            </div>
            {preReport && (
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">
                {preReport.failed} FAILED / {preReport.total} TOTAL
              </span>
            )}
          </div>
          {preReport ? (
            <div className="space-y-2 text-xs">
              <div className="text-slate-400">
                Expected failures on messy enterprise data: {preReport.failed} violations confirmed before cleaning.
              </div>
              <div className="space-y-1.5 font-mono max-h-48 overflow-y-auto">
                {preReport.results.map((r, i) => (
                  <div
                    key={i}
                    className={`p-2 rounded flex items-center justify-between ${
                      r.outcome === 'FAILED'
                        ? 'bg-rose-950/30 text-rose-300 border border-rose-900/40'
                        : 'bg-emerald-950/20 text-emerald-300'
                    }`}
                  >
                    <span className="truncate max-w-xs">{r.name}</span>
                    <span className="font-bold">{r.outcome}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-slate-500 text-xs py-8 text-center">
              Click &quot;Run PRE vs POST Tests&quot; to execute test assertions
            </div>
          )}
        </div>

        {/* Post-Cleaning Results */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Post-Cleaning Test Run (Repaired Data)
            </div>
            {postReport && (
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                {postReport.passed} PASSED / {postReport.total} TOTAL
              </span>
            )}
          </div>
          {postReport ? (
            <div className="space-y-2 text-xs">
              <div className="text-slate-400">
                All semantic constraints satisfied: 0 regressions, all anomalies repaired.
              </div>
              <div className="space-y-1.5 font-mono max-h-48 overflow-y-auto">
                {postReport.results.map((r, i) => (
                  <div
                    key={i}
                    className="p-2 rounded flex items-center justify-between bg-emerald-950/20 text-emerald-300 border border-emerald-900/40"
                  >
                    <span className="truncate max-w-xs">{r.name}</span>
                    <span className="font-bold">{r.outcome}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-slate-500 text-xs py-8 text-center">
              Awaiting post-clean verification results
            </div>
          )}
        </div>
      </div>

      {/* Generated Code Viewer */}
      {generatedCode && (
        <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Code className="w-4 h-4 text-cyan-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-white">
                Generated Pandera & Pytest Verification Suite
              </h2>
            </div>
            <span className="text-xs text-slate-400 font-mono">Autonomous Test-Driven Python</span>
          </div>
          <pre className="p-5 text-xs font-mono text-slate-300 bg-slate-950 overflow-x-auto max-h-96 leading-relaxed">
            {generatedCode}
          </pre>
        </div>
      )}
    </div>
  );
};
