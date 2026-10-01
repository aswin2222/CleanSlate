import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
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
  Layers,
  Check,
  X,
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
      <div className="p-16 text-center bg-neutral-950 border border-neutral-800 rounded-3xl">
        <Scale className="w-12 h-12 text-neutral-600 mx-auto mb-3" />
        <h3 className="text-white font-semibold text-base">No dataset selected</h3>
        <p className="text-xs text-neutral-400 mt-1">Please select or upload a dataset first</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 relative">
      {/* Top Header Card */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 shadow-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-6 relative overflow-hidden"
      >
        <div className="pointer-events-none absolute -right-10 -bottom-10 w-48 h-48 bg-cyan-500/10 rounded-full blur-2xl" />

        <div className="space-y-2 z-10">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-[10px] font-mono font-medium uppercase tracking-wider bg-white/5 text-neutral-300 border border-white/10">
              Constraint Inference Engine
            </span>
            <span className="font-mono text-xs text-neutral-400 bg-neutral-900 px-2.5 py-0.5 rounded-full border border-neutral-800">
              {selectedDataset.filename}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight uppercase">
            Semantic Constraints & Quality Rules
          </h1>
          <p className="text-xs text-neutral-400 leading-relaxed max-w-xl">
            Empirical candidate constraints discovered from profiles, validated against observed statistical boundaries.
          </p>
        </div>

        <div className="flex items-center gap-2 z-10">
          {rules.length > 0 && (
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleCreatePlan}
              className="px-6 py-2.5 rounded-full bg-white text-black font-semibold text-xs flex items-center gap-2 hover:bg-neutral-200 transition-all shadow-md cursor-pointer"
            >
              <span>Generate Cleaning Plan</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </motion.button>
          )}
        </div>
      </motion.div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-2xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs flex items-center gap-2.5"
        >
          <AlertCircle className="w-5 h-5 shrink-0 text-red-400" />
          <span>{error}</span>
        </motion.div>
      )}

      {/* Inference Controls Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="p-6 rounded-3xl bg-neutral-950 border border-neutral-800/90 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 text-xs">
            <Cpu className="w-4 h-4 text-neutral-300" />
            <span className="font-semibold text-neutral-300">Inference Mode:</span>
          </div>
          <div className="flex rounded-full bg-neutral-900 p-1 border border-neutral-800 text-xs">
            <button
              onClick={() => setLlmMode('heuristic_only')}
              className={`px-3.5 py-1.5 rounded-full font-medium transition-all cursor-pointer ${
                llmMode === 'heuristic_only'
                  ? 'bg-neutral-800 text-white shadow-sm'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              Deterministic Heuristic (Offline)
            </button>
            <button
              onClick={() => setLlmMode('llm_with_heuristic_fallback')}
              className={`px-3.5 py-1.5 rounded-full font-medium transition-all cursor-pointer ${
                llmMode === 'llm_with_heuristic_fallback'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              LLM Semantic (OpenAI / Gemini)
            </button>
          </div>
        </div>

        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={handleInferRules}
          disabled={inferring}
          className="px-5 py-2.5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-white border border-neutral-800 text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
        >
          <Sparkles className={`w-3.5 h-3.5 ${inferring ? 'animate-spin text-white' : 'text-white'}`} />
          <span>{inferring ? 'Inferring Semantic Constraints...' : 'Run Constraint Inference'}</span>
        </motion.button>
      </motion.div>

      {/* Rules Table */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="rounded-3xl bg-neutral-950 border border-neutral-800/90 overflow-hidden shadow-2xl"
      >
        <div className="px-6 py-5 border-b border-neutral-800/80 flex items-center justify-between bg-neutral-900/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-white">
                Inferred Constraints Catalog ({rules.length})
              </h2>
              <p className="text-xs text-neutral-400 font-sans">Active constraints form the basis of the clean plan</p>
            </div>
          </div>
          <span className="text-xs text-neutral-400 font-mono bg-neutral-900 px-3 py-1 rounded-full border border-neutral-800">
            <strong className="text-white font-bold">{rules.filter((r) => r.status === 'active').length}</strong> active / {rules.length} total
          </span>
        </div>

        {loading ? (
          <div className="p-16 text-center text-neutral-400 text-xs flex flex-col items-center gap-3">
            <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
            <span>Loading semantic rules...</span>
          </div>
        ) : rules.length === 0 ? (
          <div className="p-16 text-center">
            <Scale className="w-10 h-10 text-neutral-600 mx-auto mb-2" />
            <p className="text-sm text-white font-semibold">No rules inferred yet</p>
            <p className="text-xs text-neutral-400 mt-1">
              Click &quot;Run Constraint Inference&quot; above to discover data quality rules.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-neutral-900/60 text-neutral-400 uppercase tracking-wider border-b border-neutral-800/80 font-mono text-[11px]">
                <tr>
                  <th className="py-3.5 px-5">Status</th>
                  <th className="py-3.5 px-4">Rule Kind</th>
                  <th className="py-3.5 px-4">Target Columns</th>
                  <th className="py-3.5 px-4">Parameters</th>
                  <th className="py-3.5 px-4">Support / Conf.</th>
                  <th className="py-3.5 px-4">Violations</th>
                  <th className="py-3.5 px-4">Source</th>
                  <th className="py-3.5 px-5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-850 font-sans">
                {rules.map((rule) => {
                  const isActive = rule.status === 'active';
                  return (
                    <tr
                      key={rule.id}
                      className={`hover:bg-neutral-900/40 transition-colors group ${
                        !isActive ? 'opacity-40 bg-neutral-950/40' : ''
                      }`}
                    >
                      <td className="py-3.5 px-5">
                        {isActive ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium uppercase bg-white/10 text-white border border-white/20">
                            <span className="w-1.5 h-1.5 rounded-full bg-white" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium uppercase bg-neutral-900 border border-neutral-800 text-neutral-400">
                            Rejected
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-white">
                        {rule.kind}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-neutral-200 font-medium">
                        {rule.columns.join(', ')}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-neutral-400 max-w-xs truncate text-[11px]">
                        {JSON.stringify(rule.params)}
                      </td>
                      <td className="py-3.5 px-4 font-mono">
                        <span className="text-white font-bold">{(rule.support * 100).toFixed(0)}%</span>{' '}
                        <span className="text-neutral-500">/</span>{' '}
                        <span className="text-white font-bold">{(rule.confidence * 100).toFixed(0)}%</span>
                      </td>
                      <td className="py-3.5 px-4">
                        {rule.violation_count !== undefined && rule.violation_count > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium bg-neutral-900 text-neutral-300 border border-neutral-700">
                            <AlertCircle className="w-3 h-3 text-neutral-400" /> {rule.violation_count} rows
                          </span>
                        ) : (
                          <span className="text-neutral-500 font-mono text-[11px]">0</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-neutral-900 text-neutral-300 border border-neutral-800">
                          {rule.source}
                        </span>
                      </td>
                      <td className="py-3.5 px-5 text-right">
                        <button
                          onClick={() => toggleRuleStatus(rule.id)}
                          className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                            isActive
                              ? 'bg-neutral-900 hover:bg-neutral-800 text-neutral-400 hover:text-white border-neutral-800'
                              : 'bg-white hover:bg-neutral-200 text-black border-white shadow-sm'
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
      </motion.div>
    </div>
  );
};
