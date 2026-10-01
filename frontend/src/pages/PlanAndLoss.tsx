import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { apiRequest } from '../api/client';
import { Dataset, PlanStep, DryRunResult, Run } from '../types';
import { LossGauge } from '../components/LossGauge';
import {
  GitPullRequest,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  ChevronDown,
  Layers,
  Sliders,
  Check,
  Flame,
} from 'lucide-react';

interface PlanAndLossProps {
  selectedDataset: Dataset | null;
}

export const PlanAndLoss: React.FC<PlanAndLossProps> = ({ selectedDataset }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const runIdParam = searchParams.get('run_id');

  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(runIdParam);
  const [steps, setSteps] = useState<PlanStep[]>([]);
  const [cumulativeLoss, setCumulativeLoss] = useState<DryRunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch runs for current dataset
  useEffect(() => {
    if (!selectedDataset) return;
    const fetchRuns = async () => {
      try {
        const runList = await apiRequest<Run[]>(`/api/datasets/${selectedDataset.id}/runs`);
        setRuns(runList);
        if (runList.length > 0 && !activeRunId) {
          setActiveRunId(runList[0].id);
        }
      } catch (err: any) {
        console.error('Failed to fetch runs:', err);
      }
    };
    fetchRuns();
  }, [selectedDataset]);

  // Fetch plan steps and cumulative loss for active run
  useEffect(() => {
    if (!activeRunId) return;
    const fetchPlan = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiRequest<{
          steps: PlanStep[];
          cumulative_dry_run?: DryRunResult;
        }>(`/api/runs/${activeRunId}/plan`);
        setSteps(data.steps || []);
        if (data.cumulative_dry_run) {
          setCumulativeLoss(data.cumulative_dry_run);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to fetch cleaning plan');
      } finally {
        setLoading(false);
      }
    };
    fetchPlan();
  }, [activeRunId]);

  const handleGeneratePlan = async () => {
    if (!selectedDataset) return;
    try {
      setPlanning(true);
      setError(null);
      // Create new run first
      const run = await apiRequest<Run>(`/api/datasets/${selectedDataset.id}/runs`, {
        method: 'POST',
        body: JSON.stringify({ llm_mode: 'heuristic_only' }),
      });
      // Generate plan
      const planRes = await apiRequest<{
        steps: PlanStep[];
        cumulative_dry_run?: DryRunResult;
      }>(`/api/runs/${run.id}/plan`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      setRuns((prev) => [run, ...prev]);
      setActiveRunId(run.id);
      setSteps(planRes.steps);
      if (planRes.cumulative_dry_run) {
        setCumulativeLoss(planRes.cumulative_dry_run);
      }
    } catch (err: any) {
      setError(err.message || 'Plan generation failed');
    } finally {
      setPlanning(false);
    }
  };

  const [approvingStepId, setApprovingStepId] = useState<string | null>(null);

  const handleApproveStep = async (stepId: string) => {
    if (!activeRunId) return;
    const currentStep = steps.find((s) => s.id === stepId);
    if (!currentStep) return;
    const newApproved = !currentStep.approved;

    // Optimistic UI update
    setSteps((prev) =>
      prev.map((s) => (s.id === stepId ? { ...s, approved: newApproved } : s))
    );

    try {
      setApprovingStepId(stepId);
      setError(null);
      await apiRequest(`/api/runs/${activeRunId}/plan/${stepId}`, {
        method: 'PATCH',
        body: JSON.stringify({ approved: newApproved }),
      });
    } catch (err: any) {
      // Revert if API failed
      setSteps((prev) =>
        prev.map((s) => (s.id === stepId ? { ...s, approved: !newApproved } : s))
      );
      setError(err.message || 'Failed to update step approval');
    } finally {
      setApprovingStepId(null);
    }
  };

  const handleApproveAllSteps = async () => {
    if (!activeRunId) return;
    const unapproved = steps.filter((s) => s.requires_approval && !s.approved);
    if (unapproved.length === 0) return;

    // Optimistic update
    setSteps((prev) => prev.map((s) => ({ ...s, approved: true })));
    setError(null);

    try {
      setApprovingStepId('all');
      await apiRequest(`/api/runs/${activeRunId}/plan/approve-all`, {
        method: 'POST',
      });
    } catch (err: any) {
      try {
        await Promise.all(
          unapproved.map((s) =>
            apiRequest(`/api/runs/${activeRunId}/plan/${s.id}`, {
              method: 'PATCH',
              body: JSON.stringify({ approved: true }),
            })
          )
        );
      } catch (innerErr: any) {
        setError(innerErr.message || err.message || 'Failed to approve all steps');
        const data = await apiRequest<{ steps: PlanStep[] }>(`/api/runs/${activeRunId}/plan`);
        setSteps(data.steps || []);
      }
    } finally {
      setApprovingStepId(null);
    }
  };

  const handleProceedToApply = () => {
    if (!activeRunId) return;
    navigate(`/apply?run_id=${activeRunId}`);
  };

  if (!selectedDataset) {
    return (
      <div className="p-16 text-center bg-neutral-950 border border-neutral-800 rounded-3xl">
        <GitPullRequest className="w-12 h-12 text-neutral-600 mx-auto mb-3" />
        <h3 className="text-white font-semibold text-base">No dataset selected</h3>
        <p className="text-xs text-neutral-400 mt-1">Please select or upload a dataset first</p>
      </div>
    );
  }

  const unapprovedCount = steps.filter((s) => s.requires_approval && !s.approved).length;

  return (
    <div className="space-y-8 relative">
      {/* Top Header Card */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 shadow-2xl flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative overflow-hidden"
      >
        <div className="pointer-events-none absolute -right-10 -bottom-10 w-48 h-48 bg-cyan-500/10 rounded-full blur-2xl" />

        <div className="space-y-2 z-10">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-[10px] font-mono font-medium uppercase tracking-wider bg-white/5 text-neutral-300 border border-white/10">
              Deterministic Planner
            </span>
            {activeRunId && (
              <span className="font-mono text-xs text-neutral-400 bg-neutral-900 px-2.5 py-0.5 rounded-full border border-neutral-800">
                Run #{activeRunId.slice(0, 8)}
              </span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight uppercase">
            Cleaning Plan & Information Loss Model
          </h1>
          <p className="text-xs text-neutral-400 leading-relaxed max-w-xl">
            Simulates entropy drift, dropped records, and cell mutations without altering original disk state.
          </p>
        </div>

        {/* Action Buttons Toolbar */}
        <div className="flex items-center gap-3 flex-wrap z-10">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleGeneratePlan}
            disabled={planning}
            className="px-5 py-2.5 rounded-full bg-neutral-900 hover:bg-neutral-800 text-white border border-neutral-800 text-xs font-medium flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
          >
            <Sparkles className={`w-3.5 h-3.5 ${planning ? 'animate-spin text-white' : 'text-white'}`} />
            <span>{planning ? 'Synthesizing Plan...' : 'Re-Generate Plan'}</span>
          </motion.button>

          {unapprovedCount > 0 && (
            <motion.button
              whileHover={{ scale: 1.03, y: -1 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleApproveAllSteps}
              disabled={approvingStepId === 'all'}
              className="px-5 py-2.5 rounded-full bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs flex items-center gap-2 shadow-lg shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4 text-black" />
              <span>{approvingStepId === 'all' ? 'Approving All...' : `Approve All (${unapprovedCount})`}</span>
            </motion.button>
          )}

          {steps.length > 0 && (
            <motion.button
              whileHover={{ scale: 1.03, y: -1 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleProceedToApply}
              disabled={unapprovedCount > 0}
              className="px-6 py-2.5 rounded-full bg-white text-black font-semibold text-xs flex items-center gap-2 hover:bg-neutral-200 shadow-md shadow-white/5 transition-all cursor-pointer disabled:opacity-40"
            >
              <Play className="w-3.5 h-3.5 fill-black" />
              <span>Apply Reversible Plan</span>
              <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
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
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </motion.div>
      )}

      {/* Cumulative Information Loss Banner */}
      {cumulativeLoss && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="grid grid-cols-1 lg:grid-cols-3 gap-6"
        >
          <div className="lg:col-span-1">
            <LossGauge
              score={cumulativeLoss.loss_score}
              label={cumulativeLoss.loss_label}
              rowsRemovedPct={cumulativeLoss.rows_removed_pct}
              cellsModifiedPct={cumulativeLoss.cells_modified_pct}
            />
          </div>

          <div className="lg:col-span-2 p-6 rounded-3xl bg-neutral-950 border border-neutral-800/90 flex flex-col justify-between shadow-2xl relative overflow-hidden">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-neutral-400 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-white" />
                  Dry-Run Information Loss Assessment
                </span>
                <span className="text-xs font-mono text-neutral-300 font-medium bg-neutral-900 px-3 py-0.5 rounded-full border border-neutral-800">
                  Pre-Flight Simulation
                </span>
              </div>
              <p className="text-sm text-neutral-200 font-medium leading-relaxed mt-2">
                {cumulativeLoss.human_summary}
              </p>
            </div>

            <div className="grid grid-cols-3 gap-3.5 pt-5 border-t border-neutral-800/80 text-xs font-mono mt-4">
              <div className="bg-neutral-900/80 p-3.5 rounded-2xl border border-neutral-800">
                <div className="text-neutral-400 text-[10px] uppercase font-bold">Rows Purged</div>
                <div className="text-xl font-extrabold text-white mt-0.5">
                  {cumulativeLoss.rows_removed}{' '}
                  <span className="text-neutral-500 text-xs font-normal">
                    ({(cumulativeLoss.rows_removed_pct * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>
              <div className="bg-neutral-900/80 p-3.5 rounded-2xl border border-neutral-800">
                <div className="text-neutral-400 text-[10px] uppercase font-bold">Cells Mutated</div>
                <div className="text-xl font-extrabold text-white mt-0.5">
                  {cumulativeLoss.cells_modified}{' '}
                  <span className="text-neutral-500 text-xs font-normal">
                    ({(cumulativeLoss.cells_modified_pct * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>
              <div className="bg-neutral-900/80 p-3.5 rounded-2xl border border-neutral-800">
                <div className="text-neutral-400 text-[10px] uppercase font-bold">Non-Null Destroyed</div>
                <div className="text-xl font-extrabold text-white mt-0.5">
                  {cumulativeLoss.non_null_cells_destroyed}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Plan Steps List */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.1 }}
        className="rounded-3xl bg-neutral-950 border border-neutral-800/90 overflow-hidden shadow-2xl"
      >
        <div className="px-6 py-5 border-b border-neutral-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-neutral-900/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white">
              <GitPullRequest className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-white">
                Ordered Transformation Pipeline ({steps.length} Steps)
              </h2>
              <p className="text-xs text-neutral-400 font-sans">
                Strict sequential execution with reversible deltas
              </p>
            </div>
          </div>

          {unapprovedCount > 0 ? (
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs text-amber-300 font-medium flex items-center gap-1.5 bg-amber-500/10 px-3 py-1.5 rounded-full border border-amber-500/30">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                <span>{unapprovedCount} step(s) require manual approval</span>
              </span>
              <button
                onClick={handleApproveAllSteps}
                disabled={approvingStepId === 'all'}
                className="px-4 py-1.5 rounded-full bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{approvingStepId === 'all' ? 'Approving All...' : `Approve All (${unapprovedCount})`}</span>
              </button>
            </div>
          ) : steps.length > 0 ? (
            <span className="text-xs text-neutral-300 font-medium flex items-center gap-1.5 bg-neutral-900 px-3 py-1.5 rounded-full border border-neutral-800">
              <CheckCircle2 className="w-4 h-4 text-white" />
              <span>All steps approved & ready to execute</span>
            </span>
          ) : null}
        </div>

        {loading ? (
          <div className="p-16 text-center text-neutral-400 text-xs flex flex-col items-center gap-3">
            <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
            <span>Loading plan steps...</span>
          </div>
        ) : steps.length === 0 ? (
          <div className="p-16 text-center">
            <RotateCcw className="w-10 h-10 text-neutral-600 mx-auto mb-2" />
            <p className="text-sm text-neutral-300 font-semibold">No cleaning plan generated yet</p>
            <p className="text-xs text-neutral-500 mt-1">
              Click &quot;Re-Generate Plan&quot; to synthesize a verified transformation pipeline.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-neutral-850">
            {steps.map((step, idx) => {
              const isPendingApproval = step.requires_approval && !step.approved;
              const isApprovingThis = approvingStepId === step.id;

              return (
                <motion.div
                  key={step.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className={`p-6 flex flex-col md:flex-row md:items-start justify-between gap-5 transition-all duration-200 relative overflow-hidden ${
                    isPendingApproval
                      ? 'bg-amber-950/15 border-l-4 border-l-amber-400'
                      : 'hover:bg-neutral-900/40 border-l-4 border-l-neutral-700'
                  }`}
                >
                  {/* Left Column: Sequence and Details */}
                  <div className="flex items-start gap-4 min-w-0 flex-1 overflow-hidden">
                    <div
                      className={`w-10 h-10 rounded-2xl flex items-center justify-center font-extrabold font-mono text-sm shrink-0 border ${
                        isPendingApproval
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : 'bg-neutral-900 text-white border-neutral-800'
                      }`}
                    >
                      {step.seq}
                    </div>
                    <div className="min-w-0 flex-1 overflow-hidden">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="font-semibold text-white text-sm font-mono tracking-tight">
                          {step.transformation}
                        </span>
                        <span
                          className={`px-3 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase border tracking-wider ${
                            step.loss_label === 'HIGH'
                              ? 'bg-red-500/20 text-red-300 border-red-500/40'
                              : step.loss_label === 'MEDIUM'
                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                              : 'bg-neutral-900 text-white border-neutral-800'
                          }`}
                        >
                          Loss: {(step.loss_score || 0).toFixed(1)}% ({step.loss_label || 'LOW'})
                        </span>
                        {step.requires_approval && (
                          <span
                            className={`px-3 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase border flex items-center gap-1.5 ${
                              step.approved
                                ? 'bg-white/10 text-white border-white/20'
                                : 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse'
                            }`}
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                step.approved ? 'bg-white' : 'bg-amber-400'
                              }`}
                            />
                            {step.approved ? 'APPROVED' : 'REQUIRES APPROVAL'}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-neutral-300 mt-2 leading-relaxed font-normal">{step.rationale}</p>

                      {step.params && Object.keys(step.params).length > 0 && (
                        <div className="text-[11px] font-mono mt-3 bg-neutral-900/90 p-3 rounded-2xl border border-neutral-800 max-w-full overflow-x-auto flex items-center gap-2 flex-wrap">
                          <span className="text-neutral-500 font-semibold select-none flex items-center gap-1 text-[10px] uppercase tracking-wider">
                            <Sliders className="w-3 h-3 text-neutral-400" />
                            params:
                          </span>
                          {Object.entries(step.params).map(([k, v]) => (
                            <span
                              key={k}
                              className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-neutral-950 border border-neutral-800 text-[11px]"
                            >
                              <span className="text-neutral-400">{k}:</span>
                              <span className="text-white font-bold">{JSON.stringify(v)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Approve Action Button */}
                  <div className="shrink-0 flex items-center gap-2 self-start md:self-center pt-2 md:pt-0">
                    {step.requires_approval ? (
                      <motion.button
                        whileHover={{ scale: 1.04 }}
                        whileTap={{ scale: 0.96 }}
                        onClick={() => handleApproveStep(step.id)}
                        disabled={isApprovingThis}
                        className={`px-5 py-2.5 rounded-full text-xs font-semibold border flex items-center gap-2 shadow-lg transition-all cursor-pointer ${
                          step.approved
                            ? 'bg-neutral-900 hover:bg-neutral-800 text-white border-neutral-700'
                            : 'bg-amber-400 hover:bg-amber-300 text-black border-amber-400 font-bold shadow-amber-400/20'
                        }`}
                      >
                        <CheckCircle2
                          className={`w-4 h-4 ${
                            isApprovingThis ? 'animate-spin' : step.approved ? 'text-white' : 'text-black'
                          }`}
                        />
                        <span>
                          {isApprovingThis
                            ? 'Updating...'
                            : step.approved
                            ? 'Approved ✓ (Revoke)'
                            : 'Approve Step'}
                        </span>
                      </motion.button>
                    ) : (
                      <span className="px-3.5 py-1.5 rounded-full text-xs font-mono font-medium text-neutral-300 bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                        <span>Auto-Approved</span>
                      </span>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </motion.div>
    </div>
  );
};
