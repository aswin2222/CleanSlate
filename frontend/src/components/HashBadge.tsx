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
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono ${
      isMatch
        ? 'border-cyan-500/40 bg-cyan-950/70 text-cyan-300 shadow-[0_0_12px_rgba(56,189,248,0.2)]'
        : 'border-amber-800/50 bg-amber-950/80 text-amber-400'
    } ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>
      {isMatch ? (
        <ShieldCheck className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
      ) : (
        <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
      )}
      <div className="flex items-center gap-1.5 truncate">
        <span className="text-neutral-400 font-sans text-xs">SHA-256:</span>
        <span className="font-semibold text-white">{shortOriginal}</span>
        {shortCurrent && shortCurrent !== shortOriginal && (
          <>
            <span className="text-neutral-500">→</span>
            <span className="text-amber-300 font-semibold">{shortCurrent}</span>
          </>
        )}
      </div>
      {isMatch && currentHash && (
        <span className="ml-1 inline-flex items-center gap-0.5 rounded-full bg-cyan-500/20 px-2 py-0.2 text-[9px] font-bold text-cyan-300 tracking-wider border border-cyan-500/30">
          <CheckCircle2 className="w-2.5 h-2.5" /> MATCH
        </span>
      )}
    </div>
  );
};
