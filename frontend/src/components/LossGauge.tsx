import React from 'react';
import { AlertTriangle, ShieldCheck, AlertOctagon } from 'lucide-react';

interface LossGaugeProps {
  score: number; // 0 to 100
  label?: 'LOW' | 'MEDIUM' | 'HIGH' | string;
  rowsRemovedPct?: number;
  cellsModifiedPct?: number;
  entropyLoss?: number;
  compact?: boolean;
}

export const LossGauge: React.FC<LossGaugeProps> = ({
  score,
  label,
  rowsRemovedPct = 0,
  cellsModifiedPct = 0,
  entropyLoss = 0,
  compact = false,
}) => {
  const normalizedScore = Math.min(100, Math.max(0, Math.round(score * 10) / 10));
  const lossLabel = label || (normalizedScore < 15 ? 'LOW' : normalizedScore < 40 ? 'MEDIUM' : 'HIGH');

  let colorClasses = {
    bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
    bar: 'bg-emerald-500',
    badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    icon: ShieldCheck,
  };

  if (lossLabel === 'MEDIUM') {
    colorClasses = {
      bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
      bar: 'bg-amber-500',
      badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
      icon: AlertTriangle,
    };
  } else if (lossLabel === 'HIGH') {
    colorClasses = {
      bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
      bar: 'bg-rose-500',
      badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
      icon: AlertOctagon,
    };
  }

  const Icon = colorClasses.icon;

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-md border font-medium text-xs ${colorClasses.bg}`}>
        <Icon className="w-3.5 h-3.5" />
        <span>Loss: {normalizedScore}%</span>
        <span className={`px-1 rounded text-[10px] uppercase font-bold border ${colorClasses.badge}`}>
          {lossLabel}
        </span>
      </div>
    );
  }

  return (
    <div className={`p-4 rounded-xl border ${colorClasses.bg} backdrop-blur-sm shadow-lg`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5" />
          <span className="text-sm font-semibold tracking-wide text-slate-200">Predicted Information Loss</span>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${colorClasses.badge}`}>
          {lossLabel} RISK
        </span>
      </div>

      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-3xl font-extrabold tracking-tight text-white font-mono">{normalizedScore}%</span>
        <span className="text-xs text-slate-400">compound dry-run loss index</span>
      </div>

      {/* Progress Bar with safe/caution/danger threshold indicators */}
      <div className="relative w-full h-3 bg-slate-800 rounded-full overflow-hidden border border-slate-700/60 mb-4">
        <div
          className={`h-full transition-all duration-700 ease-out ${colorClasses.bar}`}
          style={{ width: `${Math.max(4, normalizedScore)}%` }}
        />
        {/* Markers for thresholds */}
        <div className="absolute top-0 bottom-0 left-[15%] w-0.5 bg-slate-600/60" title="Low/Medium Threshold (15%)" />
        <div className="absolute top-0 bottom-0 left-[40%] w-0.5 bg-slate-600/60" title="Medium/High Threshold (40%)" />
      </div>

      {/* Sub-component metrics */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-700/40 text-xs">
        <div>
          <div className="text-slate-400">Rows Removed</div>
          <div className="font-mono font-semibold text-slate-200">{(rowsRemovedPct * 100).toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-slate-400">Cells Modified</div>
          <div className="font-mono font-semibold text-slate-200">{(cellsModifiedPct * 100).toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-slate-400">Entropy Delta</div>
          <div className="font-mono font-semibold text-slate-200">{(entropyLoss * 100).toFixed(1)}%</div>
        </div>
      </div>
    </div>
  );
};
