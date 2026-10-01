import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, ShieldCheck, AlertOctagon, TrendingDown } from 'lucide-react';

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
    bg: 'bg-neutral-950 border-neutral-800 text-cyan-400',
    bar: 'from-cyan-400 to-sky-400',
    badge: 'bg-cyan-950/80 text-cyan-300 border-cyan-800/50 shadow-[0_0_10px_rgba(56,189,248,0.2)]',
    icon: ShieldCheck,
  };

  if (lossLabel === 'MEDIUM') {
    colorClasses = {
      bg: 'bg-neutral-950 border-neutral-800 text-amber-400',
      bar: 'from-amber-400 to-yellow-400',
      badge: 'bg-amber-950/80 text-amber-300 border-amber-800/50',
      icon: AlertTriangle,
    };
  } else if (lossLabel === 'HIGH') {
    colorClasses = {
      bg: 'bg-neutral-950 border-neutral-800 text-red-400',
      bar: 'from-red-400 to-rose-400',
      badge: 'bg-red-950/80 text-red-300 border-red-800/50',
      icon: AlertOctagon,
    };
  }

  const Icon = colorClasses.icon;

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold backdrop-blur-md ${colorClasses.bg}`}>
        <Icon className="w-3.5 h-3.5" />
        <span>Loss: {normalizedScore}%</span>
        <span className={`px-2 py-0.2 rounded-full text-[10px] uppercase font-mono font-bold border ${colorClasses.badge}`}>
          {lossLabel}
        </span>
      </div>
    );
  }

  return (
    <div className={`p-6 rounded-3xl border ${colorClasses.bg} shadow-2xl relative overflow-hidden group font-sans`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-neutral-900 flex items-center justify-center border border-neutral-800">
            <Icon className="w-4 h-4" />
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-white">Predicted Loss</span>
        </div>
        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border tracking-wider uppercase ${colorClasses.badge}`}>
          {lossLabel} RISK
        </span>
      </div>

      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-3xl font-extrabold tracking-tight text-white font-mono">{normalizedScore}%</span>
        <span className="text-xs text-neutral-400 font-normal">compound loss index</span>
      </div>

      {/* Progress Bar with glowing threshold indicators */}
      <div className="relative w-full h-2 bg-neutral-900 rounded-full overflow-hidden border border-neutral-800 mb-4">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(4, normalizedScore)}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={`h-full rounded-full bg-gradient-to-r ${colorClasses.bar}`}
        />
        {/* Markers for thresholds */}
        <div className="absolute top-0 bottom-0 left-[15%] w-px bg-neutral-700" title="Low Threshold (15%)" />
        <div className="absolute top-0 bottom-0 left-[40%] w-px bg-neutral-700" title="Medium Threshold (40%)" />
      </div>

      {/* Sub-component metrics */}
      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-neutral-800 text-xs font-mono">
        <div>
          <div className="text-neutral-500 text-[10px] uppercase font-bold">Rows Purged</div>
          <div className="font-bold text-white text-sm mt-0.5">{(rowsRemovedPct * 100).toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-neutral-500 text-[10px] uppercase font-bold">Mutations</div>
          <div className="font-bold text-teal-400 text-sm mt-0.5">{(cellsModifiedPct * 100).toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-neutral-500 text-[10px] uppercase font-bold">Entropy Δ</div>
          <div className="font-bold text-white text-sm mt-0.5">{(entropyLoss || 0).toFixed(2)}</div>
        </div>
      </div>
    </div>
  );
};
