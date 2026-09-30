import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
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

  const handleApproveStep = (stepId: string) => {
    setSteps((prev) =>
      prev.map((s) => (s.id === stepId ? { ...s, approved: !s.approved } : s))
    );
  };

  const handleProceedToApply = () => {
    if (!activeRunId) return;
    navigate(`/apply?run_id=${activeRunId}`);
  };

  if (!selectedDataset) {
    return (
      <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl">
        <GitPullRequest className="w-12 h-12 text-slate-600 mx-auto mb-3" />
        <h3 className="text-white font-semibold text-sm">No dataset selected</h3>
        <p className="text-xs text-slate-400 mt-1">Please select or upload a dataset first</p>
      </div>
    );
  }

  const unapprovedCount = steps.filter((s) => s.requires_approval && !s.approved).length;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Cleaning Plan & Loss Estimation:{' '}
            <span className="text-indigo-400 font-mono">{selectedDataset.filename}</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Calculates dry-run entropy drift, rows dropped, and cells modified before mutating any state.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleGeneratePlan}
            disabled={planning}
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 text-xs font-semibold flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <Sparkles className={`w-3.5 h-3.5 ${planning ? 'animate-spin' : ''}`} />
            {planning ? 'Synthesizing...' : 'Re-Generate Plan'}
          </button>

          {steps.length > 0 && (
            <button
              onClick={handleProceedToApply}
              disabled={unapprovedCount > 0}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              <span>Apply Reversible Plan</span>
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

      {/* Cumulative Information Loss Banner */}
      {cumulativeLoss && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1">
            <LossGauge
              score={cumulativeLoss.loss_score}
              label={cumulativeLoss.loss_label}
              rowsRemovedPct={cumulativeLoss.rows_removed_pct}
              cellsModifiedPct={cumulativeLoss.cells_modified_pct}
            />
          </div>

          <div className="md:col-span-2 p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
                Dry-Run Information Loss Assessment
              </div>
              <p className="text-sm text-slate-200 font-medium">
                {cumulativeLoss.human_summary}
              </p>
            </div>

            <div className="grid grid-cols-3 gap-3 pt-4 border-t border-slate-800 text-xs font-mono">
              <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-700/50">
                <div className="text-slate-400 text-[10px]">Rows Purged</div>
                <div className="text-base font-bold text-white">
                  {cumulativeLoss.rows_removed}{' '}
                  <span className="text-slate-500 text-xs">
                    ({(cumulativeLoss.rows_removed_pct * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>
              <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-700/50">
                <div className="text-slate-400 text-[10px]">Cells Mutated</div>
                <div className="text-base font-bold text-cyan-400">
                  {cumulativeLoss.cells_modified}{' '}
                  <span className="text-slate-500 text-xs">
                    ({(cumulativeLoss.cells_modified_pct * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>
              <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-700/50">
                <div className="text-slate-400 text-[10px]">Non-Null Destroyed</div>
                <div className="text-base font-bold text-amber-400">
                  {cumulativeLoss.non_null_cells_destroyed}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Plan Steps List */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitPullRequest className="w-4 h-4 text-indigo-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-white">
              Ordered Transformation Pipeline ({steps.length} Steps)
            </h2>
          </div>
          {unapprovedCount > 0 && (
            <span className="text-xs text-amber-400 font-semibold flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" /> {unapprovedCount} step(s) require manual approval
            </span>
          )}
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 text-xs">Loading plan steps...</div>
        ) : steps.length === 0 ? (
          <div className="p-12 text-center">
            <RotateCcw className="w-10 h-10 text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-slate-300 font-medium">No cleaning plan generated yet</p>
            <p className="text-xs text-slate-500 mt-1">
              Click &quot;Re-Generate Plan&quot; to synthesize a verified transformation pipeline
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {steps.map((step) => (
              <div
                key={step.id}
                className={`p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-colors ${
                  step.requires_approval && !step.approved ? 'bg-amber-950/20' : 'hover:bg-slate-800/20'
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 flex items-center justify-center font-bold font-mono text-sm shrink-0">
                    {step.seq}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-white text-sm font-mono">
                        {step.transformation}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                          step.loss_label === 'HIGH'
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                            : step.loss_label === 'MEDIUM'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        }`}
                      >
                        Loss: {(step.loss_score || 0).toFixed(1)}% ({step.loss_label || 'LOW'})
                      </span>
                      {step.requires_approval && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                          REQUIRES APPROVAL
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-300 mt-1">{step.rationale}</p>
                    <div className="text-[11px] text-slate-500 font-mono mt-1">
                      params: {JSON.stringify(step.params)}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0 self-end md:self-center">
                  {step.requires_approval && (
                    <button
                      onClick={() => handleApproveStep(step.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold border flex items-center gap-1.5 transition-all ${
                        step.approved
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                          : 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border-amber-500/40'
                      }`}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {step.approved ? 'Approved' : 'Approve Step'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
