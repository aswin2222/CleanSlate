import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { Dataset, Rule, Run } from '../types';
import {
  Scale,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle,
  XCircle,
  AlertCircle,
  Cpu,
} from 'lucide-react';

interface RulesProps {
  selectedDataset: Dataset | null;
}

export const Rules: React.FC<RulesProps> = ({ selectedDataset }) => {
  const navigate = useNavigate();
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(false);
  const [inferring, setInferring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llmMode, setLlmMode] = useState<'heuristic_only' | 'llm_with_heuristic_fallback'>('heuristic_only');

  const fetchRules = async () => {
    if (!selectedDataset) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiRequest<Rule[]>(`/api/datasets/${selectedDataset.id}/rules`);
      setRules(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch rules');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, [selectedDataset]);

  const handleInferRules = async () => {
    if (!selectedDataset) return;
    try {
      setInferring(true);
      setError(null);
      const res = await apiRequest<{ rules: Rule[]; inferred_count: number }>(
        `/api/datasets/${selectedDataset.id}/infer`,
        {
          method: 'POST',
          body: JSON.stringify({ mode: llmMode }),
        }
      );
      setRules(res.rules);
    } catch (err: any) {
      setError(err.message || 'Rule inference failed');
    } finally {
      setInferring(false);
    }
  };

  const toggleRuleStatus = (ruleId: string) => {
    setRules((prev) =>
      prev.map((r) =>
        r.id === ruleId ? { ...r, status: r.status === 'active' ? 'rejected' : 'active' } : r
      )
    );
  };

  const handleCreatePlan = async () => {
    if (!selectedDataset) return;
    try {
      const activeRules = rules.filter((r) => r.status === 'active');
      const run = await apiRequest<Run>(`/api/datasets/${selectedDataset.id}/runs`, {
        method: 'POST',
        body: JSON.stringify({ llm_mode: llmMode }),
      });
      // Generate plan for run
      await apiRequest(`/api/runs/${run.id}/plan`, {
        method: 'POST',
        body: JSON.stringify({ rules: activeRules }),
      });
      navigate(`/plan?run_id=${run.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to generate plan');
    }
  };

  if (!selectedDataset) {
    return (
      <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl">
        <Scale className="w-12 h-12 text-slate-600 mx-auto mb-3" />
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
            Semantic Constraints & Rules: <span className="text-indigo-400 font-mono">{selectedDataset.filename}</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Empirical candidates generated from profile patterns and strictly verified against observed distribution thresholds.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {rules.length > 0 && (
            <button
              onClick={handleCreatePlan}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all"
            >
              <span>Generate Cleaning Plan</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
          {error}
        </div>
      )}

      {/* Inference Controls Card */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs">
            <Cpu className="w-4 h-4 text-indigo-400" />
            <span className="font-semibold text-slate-300">Inference Engine:</span>
          </div>
          <div className="flex rounded-lg bg-slate-800 p-0.5 border border-slate-700 text-xs">
            <button
              onClick={() => setLlmMode('heuristic_only')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                llmMode === 'heuristic_only'
                  ? 'bg-indigo-600 text-white font-semibold shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Deterministic Heuristic (Fast & Offline)
            </button>
            <button
              onClick={() => setLlmMode('llm_with_heuristic_fallback')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                llmMode === 'llm_with_heuristic_fallback'
                  ? 'bg-indigo-600 text-white font-semibold shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              LLM Semantic (OpenAI / Heuristic Fallback)
            </button>
          </div>
        </div>

        <button
          onClick={handleInferRules}
          disabled={inferring}
          className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 text-xs font-semibold flex items-center gap-2 transition-all disabled:opacity-50"
        >
          <Sparkles className={`w-3.5 h-3.5 ${inferring ? 'animate-spin' : ''}`} />
          {inferring ? 'Inferring Semantic Constraints...' : 'Run Constraint Inference'}
        </button>
      </div>

      {/* Rules Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-white">
              Inferred Rules ({rules.length})
            </h2>
          </div>
          <span className="text-xs text-slate-400">
            {rules.filter((r) => r.status === 'active').length} active / {rules.length} total
          </span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 text-xs">Loading rules...</div>
        ) : rules.length === 0 ? (
          <div className="p-12 text-center">
            <Scale className="w-10 h-10 text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-slate-300 font-medium">No rules inferred yet</p>
            <p className="text-xs text-slate-500 mt-1">
              Click &quot;Run Constraint Inference&quot; above to discover data quality rules
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Rule Kind</th>
                  <th className="py-3 px-4">Target Columns</th>
                  <th className="py-3 px-4">Parameters</th>
                  <th className="py-3 px-4">Support / Conf.</th>
                  <th className="py-3 px-4">Violations</th>
                  <th className="py-3 px-4">Source</th>
                  <th className="py-3 px-4 text-right">Toggle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {rules.map((rule) => {
                  const isActive = rule.status === 'active';
                  return (
                    <tr
                      key={rule.id}
                      className={`hover:bg-slate-800/30 transition-colors ${
                        !isActive ? 'opacity-50 bg-slate-950/40' : ''
                      }`}
                    >
                      <td className="py-3 px-4">
                        {isActive ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                            <CheckCircle className="w-3.5 h-3.5" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-slate-500 font-semibold text-[11px]">
                            <XCircle className="w-3.5 h-3.5" /> Rejected
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-white">
                        {rule.kind}
                      </td>
                      <td className="py-3 px-4 font-mono text-cyan-300">
                        {rule.columns.join(', ')}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400 max-w-xs truncate">
                        {JSON.stringify(rule.params)}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        <span className="text-emerald-400">{(rule.support * 100).toFixed(0)}%</span> /{' '}
                        <span className="text-indigo-400">{(rule.confidence * 100).toFixed(0)}%</span>
                      </td>
                      <td className="py-3 px-4">
                        {rule.violation_count !== undefined && rule.violation_count > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                            <AlertCircle className="w-3 h-3" /> {rule.violation_count} rows
                          </span>
                        ) : (
                          <span className="text-slate-500 font-mono">0</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${
                            rule.source === 'llm'
                              ? 'bg-purple-500/10 text-purple-400 border-purple-500/30'
                              : 'bg-slate-800 text-slate-300 border-slate-700'
                          }`}
                        >
                          {rule.source}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => toggleRuleStatus(rule.id)}
                          className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
                            isActive
                              ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border-rose-500/30'
                              : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                          }`}
                        >
                          {isActive ? 'Reject' : 'Accept'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
