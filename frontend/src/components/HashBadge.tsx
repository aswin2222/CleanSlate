import React from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface HashBadgeProps {
  originalHash: string;
  currentHash?: string;
  isRollbackMatch?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const HashBadge: React.FC<HashBadgeProps> = ({
  originalHash,
  currentHash,
  isRollbackMatch,
  size = 'md',
}) => {
  const shortOriginal = originalHash ? `${originalHash.slice(0, 8)}...${originalHash.slice(-8)}` : 'N/A';
  const shortCurrent = currentHash ? `${currentHash.slice(0, 8)}...${currentHash.slice(-8)}` : null;
  const isMatch = isRollbackMatch ?? (currentHash ? originalHash === currentHash : true);

  return (
    <div className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 font-mono ${
      isMatch
        ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
        : 'border-amber-500/30 bg-amber-500/10 text-amber-400'
    } ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>
      {isMatch ? (
        <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
      ) : (
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
      )}
      <div className="flex items-center gap-2 truncate">
        <span className="text-slate-400 font-sans text-xs">SHA-256:</span>
        <span className="font-semibold">{shortOriginal}</span>
        {shortCurrent && shortCurrent !== shortOriginal && (
          <>
            <span className="text-slate-500">→</span>
            <span className="text-amber-300 font-semibold">{shortCurrent}</span>
          </>
        )}
      </div>
      {isMatch && currentHash && (
        <span className="ml-1 inline-flex items-center gap-0.5 rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-bold text-emerald-300 tracking-wider">
          <CheckCircle2 className="w-2.5 h-2.5" /> MATCH
        </span>
      )}
    </div>
  );
};
