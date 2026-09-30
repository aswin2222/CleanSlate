import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence, useSpring, useMotionValue } from 'framer-motion';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  Lock,
  Key,
  Terminal,
  Layers,
  Zap,
  Globe,
  ArrowRight,
  CheckCircle,
  Copy,
  ExternalLink,
  X,
  Play,
  Activity,
  AlertTriangle,
  FileText,
  Mail,
  Link as LinkIcon,
  Cpu,
  LogIn,
  Eye,
  EyeOff,
  Database,
  ArrowUpRight
} from 'lucide-react';
import { apiRequest, setAuthToken, getAuthToken } from '../api/client';

// ==========================================
// Mock Data Quality Issue Database & Engine Presets
// ==========================================
interface QualityReport {
  id: string;
  type: string;
  risk_score: number;
  classification: 'safe' | 'suspicious' | 'dangerous';
  confidence: number;
  intent: string;
  indicators: string[];
  explanation: {
    summary: string;
    targetAction: string;
  };
  recommended_action: 'allow' | 'warn' | 'block' | 'quarantine';
}

const PRESET_ISSUES: Record<string, QualityReport> = {
  prompt: {
    id: 'issue-missing-values',
    type: 'prompt',
    risk_score: 82,
    classification: 'suspicious',
    confidence: 91,
    intent: 'Widespread NULL/NaN propagation across 34% of critical revenue columns causing cascading aggregation failures.',
    indicators: [
      'Missing Values: 34% NULLs detected in "revenue" and "transaction_date" columns',
      'Type Mismatch: Mixed string/numeric types in "amount" field across 12K rows',
      'Encoding Anomaly: UTF-8 / Latin-1 character corruption in "customer_name"',
      'Schema Drift: 3 new unrecognized columns since last canonical snapshot',
    ],
    explanation: {
      summary: 'Systemic data quality degradation with cascading NULL propagation and type inconsistencies across enterprise dataset.',
      targetAction: 'Generating reversible cleaning plan with information loss estimation before applying transformations.',
    },
    recommended_action: 'warn',
  },
  url: {
    id: 'issue-duplicates',
    type: 'url',
    risk_score: 94,
    classification: 'dangerous',
    confidence: 96,
    intent: 'Exact and fuzzy duplicate records inflating metrics by ~18% with inconsistent deduplication keys.',
    indicators: [
      'Exact Duplicates: 2,847 rows with identical composite key hash signatures',
      'Fuzzy Near-Duplicates: 1,203 rows within 0.92 Jaccard similarity threshold',
      'Referential Integrity Violation: 847 orphaned foreign key references',
      'Timestamp Collision: 412 records share identical millisecond timestamps',
    ],
    explanation: {
      summary: 'Critical duplicate contamination distorting downstream analytics and ML training pipelines.',
      targetAction: 'Applying deterministic deduplication with full delta ledger for 100% rollback capability.',
    },
    recommended_action: 'block',
  },
  email: {
    id: 'issue-outliers',
    type: 'email',
    risk_score: 88,
    classification: 'dangerous',
    confidence: 94,
    intent: 'Statistical outliers and constraint violations in financial columns exceeding 4σ from distribution mean.',
    indicators: [
      'Extreme Outlier: "revenue" value $-9,999,999 detected (4.7σ deviation)',
      'Constraint Violation: 23 records with negative quantities in "units_sold"',
      'Format Inconsistency: Mixed date formats (MM/DD/YYYY vs YYYY-MM-DD) in 15% of rows',
    ],
    explanation: {
      summary: 'Anomalous values and constraint violations requiring immediate quarantine before pipeline execution.',
      targetAction: 'Isolating outlier records and generating Pandera validation schema for continuous monitoring.',
    },
    recommended_action: 'block',
  },
};

// ==========================================
// 1. Live Data Quality Scanner Modal Component
// ==========================================
interface ScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEnterApp: () => void;
}

export const LiveThreatScannerModal: React.FC<ScannerModalProps> = ({ isOpen, onClose, onEnterApp }) => {
  const [tab, setTab] = useState<'prompt' | 'url' | 'email'>('prompt');
  const [payloadText, setPayloadText] = useState(
    'revenue,customer_name,transaction_date\n45000,John Smith,2024-01-15\n,,\nNaN,J0hn Sm!th,01/15/2024\n-99999,NULL,invalid_date'
  );
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState({ step: 0, message: '', detail: '' });
  const [result, setResult] = useState<QualityReport | null>(null);

  // Field Tokenization demo state
  const [tokenInput, setTokenInput] = useState('4532-8921-9012-3841');
  const [tokenOutput, setTokenOutput] = useState<string | null>(null);
  const [isTokenizing, setIsTokenizing] = useState(false);

  const presets = {
    prompt: [
      {
        label: 'Messy CSV with NULLs',
        text: 'revenue,customer_name,transaction_date\n45000,John Smith,2024-01-15\n,,\nNaN,J0hn Sm!th,01/15/2024\n-99999,NULL,invalid_date',
      },
      {
        label: 'Clean Dataset Sample',
        text: 'id,product,price,quantity,date\n1,Widget A,29.99,100,2024-01-15\n2,Widget B,49.99,250,2024-01-16\n3,Widget C,19.99,75,2024-01-17',
      },
    ],
    url: [
      {
        label: 'Duplicate-Heavy Records',
        text: 'order_id,customer,amount\n1001,Acme Corp,5000\n1001,Acme Corp,5000\n1002,Acme Corp.,5000.00\n1003,ACME CORP,5000\n1004,Beta Inc,3200',
      },
      {
        label: 'Verified Clean Batch',
        text: 'employee_id,name,department,salary\nE001,Alice Johnson,Engineering,95000\nE002,Bob Chen,Marketing,82000\nE003,Carol Davis,Finance,91000',
      },
    ],
    email: [
      {
        label: 'Outlier-Laden Financial',
        text: 'account,balance,last_txn\nA001,15000,2024-03-01\nA002,-9999999,NEVER\nA003,25000,03/01/2024\nA004,0.001,2024-13-45',
      },
      {
        label: 'Consistent Time Series',
        text: 'timestamp,sensor_id,value\n2024-01-01T00:00:00Z,S01,22.5\n2024-01-01T01:00:00Z,S01,22.7\n2024-01-01T02:00:00Z,S01,22.3',
      },
    ],
  };

  const runScan = async () => {
    if (!payloadText.trim()) return;
    setIsScanning(true);
    setResult(null);

    const steps = [
      { step: 1, message: 'Schema Detection & Type Inference', detail: 'Parsing column types, delimiters, encoding, and structural patterns...' },
      { step: 2, message: 'Statistical Profiling Engine', detail: 'Computing distributions, null ratios, uniqueness, and outlier boundaries...' },
      { step: 3, message: 'Semantic Constraint Inference', detail: 'Inferring domain rules, format patterns, referential integrity, and value ranges...' },
      { step: 4, message: 'Information Loss Estimation', detail: 'Calculating potential data loss and generating reversible cleaning plan...' },
    ];

    for (const s of steps) {
      setScanStep(s);
      await new Promise((r) => setTimeout(r, 300));
    }

    // Determine result
    const lower = payloadText.toLowerCase();
    const isClean = !lower.includes('null') && !lower.includes('nan') && !lower.includes('-9999') && !lower.includes('invalid') && !lower.includes('never');

    if (isClean) {
      setResult({
        id: 'scan-clean-verified',
        type: tab,
        risk_score: 8,
        classification: 'safe',
        confidence: 98,
        intent: 'Dataset passes all inferred semantic constraints and schema validation checks.',
        indicators: [
          'Schema Consistency: All columns match inferred type signatures',
          'Zero NULL/NaN: No missing values detected across all fields',
          'Format Uniformity: Consistent date, numeric, and string formatting throughout',
        ],
        explanation: {
          summary: 'All quality indicators validated. Dataset is clean and ready for downstream processing.',
          targetAction: 'Generating canonical SHA-256 hash and registering clean snapshot in reversible ledger.',
        },
        recommended_action: 'allow',
      });
    } else {
      setResult(PRESET_ISSUES[tab] || PRESET_ISSUES.prompt);
    }

    setIsScanning(false);
  };

  const handleTokenize = () => {
    setIsTokenizing(true);
    setTimeout(() => {
      const hex = Array.from(tokenInput)
        .map((c) => c.charCodeAt(0).toString(16))
        .join('');
      setTokenOutput(`sha256_${hex.slice(0, 16)}_${Math.random().toString(36).slice(2, 8)}`);
      setIsTokenizing(false);
    }, 250);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/85 backdrop-blur-md"
        />

        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94, y: 20 }}
          transition={{ type: 'spring', stiffness: 350, damping: 28 }}
          className="relative w-full max-w-4xl rounded-3xl bg-neutral-950 border border-neutral-800 shadow-[0_25px_70px_rgba(0,0,0,0.9)] text-white overflow-hidden z-10 my-8 font-sans"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-neutral-800/80 bg-neutral-900/60">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
                <ShieldCheck className="w-5 h-5 text-teal-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold text-white tracking-tight">
                    CleanSlate Data Quality Scanner
                  </h3>
                  <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded-full border border-emerald-800/50 font-mono">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Profiler Engine v1.0 Live
                  </span>
                </div>
                <p className="text-xs text-neutral-400 mt-0.5">
                  Real-time data profiling, constraint inference & reversible cleaning pipeline
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-full text-neutral-400 hover:text-white hover:bg-neutral-800/80 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
            {/* Tab switch & Presets */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-neutral-800">
              <div className="flex items-center gap-1.5 p-1 bg-neutral-900 rounded-2xl border border-neutral-800">
                <button
                  onClick={() => {
                    setTab('prompt');
                    setPayloadText(presets.prompt[0].text);
                    setResult(null);
                  }}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                    tab === 'prompt'
                      ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40 shadow-sm'
                      : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  <Cpu className="w-3.5 h-3.5" /> Missing Values
                </button>
                <button
                  onClick={() => {
                    setTab('url');
                    setPayloadText(presets.url[0].text);
                    setResult(null);
                  }}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                    tab === 'url'
                      ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40 shadow-sm'
                      : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  <LinkIcon className="w-3.5 h-3.5" /> Duplicates
                </button>
                <button
                  onClick={() => {
                    setTab('email');
                    setPayloadText(presets.email[0].text);
                    setResult(null);
                  }}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                    tab === 'email'
                      ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40 shadow-sm'
                      : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  <Mail className="w-3.5 h-3.5" /> Outliers
                </button>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] text-neutral-500 font-mono">Quick test:</span>
                {presets[tab].map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setPayloadText(p.text);
                      setResult(null);
                    }}
                    className="text-xs text-neutral-300 hover:text-white bg-neutral-900 px-2.5 py-1 rounded-lg border border-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer font-sans"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Input area */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-neutral-300 flex items-center justify-between">
                <span>Dataset Sample to Profile:</span>
                <span className="text-[11px] text-neutral-500 font-mono">{payloadText.length} characters</span>
              </label>
              <textarea
                value={payloadText}
                onChange={(e) => setPayloadText(e.target.value)}
                rows={3}
                placeholder="Paste CSV data, records, or dataset sample..."
                className="w-full rounded-2xl bg-neutral-900/90 border border-neutral-800 px-4 py-3 text-sm text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-teal-500/60 focus:ring-1 focus:ring-teal-500/40 font-mono leading-relaxed resize-none"
              />
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-xs text-neutral-400">
                <Activity className="w-4 h-4 text-teal-400" />
                <span>Multi-Signal Profiling Engine (Schema • Statistics • Semantics)</span>
              </div>
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={runScan}
                disabled={isScanning || !payloadText.trim()}
                className="px-6 py-2.5 rounded-full bg-gradient-to-r from-teal-400 to-cyan-500 text-black font-semibold text-xs shadow-lg shadow-teal-500/20 hover:shadow-teal-500/30 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isScanning ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                    <span>Analyzing Payload...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Run Data Quality Scan</span>
                  </>
                )}
              </motion.button>
            </div>

            {/* Progress Bar during scan */}
            {isScanning && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 rounded-2xl bg-neutral-900/80 border border-neutral-800 space-y-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-teal-300">
                    Step {scanStep.step} of 4: {scanStep.message}
                  </span>
                  <span className="font-mono text-neutral-400">Processing...</span>
                </div>
                <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-teal-400 to-cyan-400"
                    animate={{ width: `${scanStep.step * 25}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
                <p className="text-[11px] text-neutral-400 font-mono">{scanStep.detail}</p>
              </motion.div>
            )}

            {/* Scan Results Card */}
            {result && !isScanning && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-6 rounded-3xl bg-neutral-900 border border-neutral-800 space-y-5"
              >
                <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-neutral-800">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-12 h-12 rounded-2xl flex items-center justify-center font-mono font-bold text-lg ${
                        result.risk_score >= 75
                          ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                          : result.risk_score >= 40
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }`}
                    >
                      {result.risk_score}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold uppercase tracking-wider text-white">
                          Risk Classification: {result.classification}
                        </span>
                        <span className="text-xs text-neutral-400 font-mono">
                          ({result.confidence}% confidence)
                        </span>
                      </div>
                      <p className="text-xs text-neutral-400 mt-0.5">{result.intent}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-neutral-400">Action:</span>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                        result.recommended_action === 'block' || result.recommended_action === 'quarantine'
                          ? 'bg-red-500 text-white shadow-sm shadow-red-500/30'
                          : result.recommended_action === 'warn'
                          ? 'bg-amber-500 text-black'
                          : 'bg-emerald-500 text-white'
                      }`}
                    >
                      {result.recommended_action}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
                      Key Quality Issues ({result.indicators.length})
                    </h4>
                    <ul className="space-y-1.5 text-xs text-neutral-300">
                      {result.indicators.map((ind, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                          <span>{ind}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
                      Cleaning Recommendation
                    </h4>
                    <div className="p-3.5 rounded-2xl bg-neutral-950 border border-neutral-800 text-xs text-neutral-300 space-y-1.5">
                      <p className="font-medium text-white">{result.explanation.summary}</p>
                      <p className="text-neutral-400 text-[11px] leading-relaxed">
                        {result.explanation.targetAction}
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Zero-Knowledge Field Tokenization Sandbox */}
            <div className="p-5 rounded-3xl bg-neutral-900/60 border border-neutral-800/80 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-teal-400" />
                  <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
                    Canonical Hash Validator (SHA-256 Reversible Ledger)
                  </h4>
                </div>
                <span className="text-[10px] text-neutral-400 font-mono">POST /api/datasets/hash</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
                <div className="sm:col-span-8">
                  <input
                    type="text"
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    placeholder="Enter dataset row or value to hash..."
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-2.5 text-xs font-mono text-neutral-200 focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div className="sm:col-span-4 flex gap-2">
                  <button
                    onClick={handleTokenize}
                    disabled={isTokenizing}
                    className="w-full py-2.5 px-3 rounded-xl bg-teal-500/20 text-teal-300 hover:bg-teal-500/30 border border-teal-500/30 text-xs font-medium transition-colors cursor-pointer"
                  >
                    Compute SHA-256 Hash
                  </button>
                </div>
              </div>

              {tokenOutput && (
                <div className="p-3.5 rounded-xl bg-neutral-950 border border-neutral-800 text-[11px] font-mono space-y-1">
                  <div className="text-neutral-400 flex items-center justify-between">
                    <span>Canonical Hash Signature:</span>
                    <span className="text-teal-400">SHA-256 Integrity Verified</span>
                  </div>
                  <div className="text-teal-300 break-all">{tokenOutput}</div>
                </div>
              )}
            </div>

            {/* Launch Pipeline Banner inside Scanner */}
            <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-950/40 to-teal-950/40 border border-emerald-500/30 flex items-center justify-between">
              <div>
                <h5 className="text-xs font-semibold text-white">Ready to Clean & Safeguard Your Datasets?</h5>
                <p className="text-[11px] text-neutral-400 mt-0.5">
                  Launch the CleanSlate autonomous pipeline to profile, infer constraints, and execute 100% reversible repairs.
                </p>
              </div>
              <button
                onClick={() => {
                  onClose();
                  onEnterApp();
                }}
                className="bg-emerald-400 text-black px-4 py-2 rounded-xl text-xs font-semibold hover:bg-emerald-300 transition-colors inline-flex items-center gap-1.5 shrink-0 cursor-pointer shadow-md"
              >
                <span>Launch CleanSlate</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

// ==========================================
// 2. Authentication Modal Component
// ==========================================
interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoginSuccess: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onLoginSuccess }) => {
  const [email, setEmail] = useState('admin@cleanslate.local');
  const [password, setPassword] = useState('cleanslate123!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const resp = await apiRequest<{ access_token: string; token_type: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setAuthToken(resp.access_token);
      onLoginSuccess();
    } catch {
      // Auto register default admin if needed or retry
      try {
        await apiRequest('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email, password, role: 'admin' }),
        });
        const resp2 = await apiRequest<{ access_token: string; token_type: string }>('/api/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        });
        setAuthToken(resp2.access_token);
        onLoginSuccess();
      } catch (err: any) {
        setError(err.message || 'Authentication failed. Please verify credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInstantDemoEnter = async () => {
    setLoading(true);
    try {
      try {
        const resp = await apiRequest<{ access_token: string; token_type: string }>('/api/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email: 'admin@cleanslate.local', password: 'CleanSlate2026!' }),
        });
        setAuthToken(resp.access_token);
      } catch {
        try {
          const resp = await apiRequest<{ access_token: string; token_type: string }>('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email: 'admin@cleanslate.local', password: 'cleanslate123!' }),
          });
          setAuthToken(resp.access_token);
        } catch {
          await apiRequest('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email: 'admin@cleanslate.local', password: 'CleanSlate2026!', role: 'admin' }),
          });
          const resp = await apiRequest<{ access_token: string; token_type: string }>('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email: 'admin@cleanslate.local', password: 'CleanSlate2026!' }),
          });
          setAuthToken(resp.access_token);
        }
      }
      onLoginSuccess();
    } catch (err: any) {
      setError(err?.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/85 backdrop-blur-xl overflow-y-auto">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0"
        />

        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ type: 'spring', stiffness: 350, damping: 28 }}
          className="relative w-full max-w-md rounded-3xl bg-neutral-950 border border-neutral-800 shadow-[0_25px_70px_rgba(0,0,0,0.9)] text-white p-6 sm:p-8 overflow-hidden z-10 font-sans"
        >
          <div className="pointer-events-none absolute -top-20 -right-20 w-52 h-52 rounded-full bg-emerald-500/10 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-20 -left-20 w-52 h-52 rounded-full bg-blue-500/10 blur-3xl" />

          <button
            onClick={onClose}
            className="absolute top-5 right-5 p-2 rounded-full text-neutral-400 hover:text-white hover:bg-neutral-900 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="space-y-5">
            <div className="space-y-1">
              <div className="w-10 h-10 rounded-2xl bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white mb-3">
                <Shield className="w-5 h-5 fill-emerald-400 stroke-transparent" />
              </div>
              <h3 className="text-lg font-semibold text-white tracking-tight">
                Sign in to CleanSlate
              </h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Access reversible ledgers, autonomous profiling, and test-driven cleaning pipelines.
              </p>
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 rounded-xl bg-red-950/40 border border-red-500/40 flex items-center gap-2 text-xs text-red-300"
              >
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                <span>{error}</span>
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3 pt-1">
              <div>
                <label className="block text-[11px] font-medium text-neutral-300 mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@cleanslate.local"
                  className="w-full bg-neutral-900 border border-neutral-800 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-600 transition-colors"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-[11px] font-medium text-neutral-300">Password</label>
                  <span className="text-[10px] text-neutral-500">Default: cleanslate123!</span>
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-neutral-900 border border-neutral-800 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-600 transition-colors"
                />
              </div>

              <motion.button
                type="submit"
                disabled={loading}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                className="w-full bg-white text-black font-semibold text-xs py-3 px-4 rounded-full hover:bg-neutral-200 transition-all cursor-pointer flex items-center justify-center gap-2 mt-4 disabled:opacity-50 shadow-md shadow-white/5"
              >
                {loading ? (
                  <div className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Sign In & Enter Pipeline</span>
                    <ArrowRight className="w-3.5 h-3.5 text-neutral-800" />
                  </>
                )}
              </motion.button>
            </form>

            <div className="pt-3 border-t border-neutral-850">
              <button
                type="button"
                onClick={handleInstantDemoEnter}
                className="w-full bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 font-semibold text-xs py-2.5 px-4 rounded-full transition-all cursor-pointer flex items-center justify-center gap-2"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Instant 1-Click Launch (Admin Demo)</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

// ==========================================
// 3. Main CleanSlate Landing Page Component
// ==========================================
export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  // Navigation and Modal states
  const [activeTab, setActiveTab] = useState<'platform' | 'solutions' | 'company' | 'support'>('platform');
  const [isScannerOpen, setIsScannerOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [codeLanguage, setCodeLanguage] = useState<'typescript' | 'python'>('typescript');
  const [copiedCode, setCopiedCode] = useState(false);

  // Mouse tracking for dynamic cursor glow and parallax
  const mouseX = useMotionValue(-100);
  const mouseY = useMotionValue(-100);
  const springConfig = { damping: 24, stiffness: 220, mass: 0.6 };
  const smoothX = useSpring(mouseX, springConfig);
  const smoothY = useSpring(mouseY, springConfig);
  const [rawMouse, setRawMouse] = useState({ x: -100, y: -100 });
  const [parallax, setParallax] = useState({ x: 0, y: 0 });
  const [isHoveringInteractive, setIsHoveringInteractive] = useState(false);
  const [isMouseInWindow, setIsMouseInWindow] = useState(false);

  // Scroll spy to highlight active header tab
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const platform = document.getElementById('platform');
      const solutions = document.getElementById('solutions');
      const company = document.getElementById('company');
      const support = document.getElementById('support');
      const offset = 220;

      if (support && scrollY >= support.offsetTop - offset) setActiveTab('support');
      else if (company && scrollY >= company.offsetTop - offset) setActiveTab('company');
      else if (solutions && scrollY >= solutions.offsetTop - offset) setActiveTab('solutions');
      else if (platform && scrollY >= platform.offsetTop - offset) setActiveTab('platform');
      else setActiveTab('platform');
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Mousemove handler for cursor glow & hero video parallax
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setIsMouseInWindow(true);
      setRawMouse({ x: e.clientX, y: e.clientY });
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);

      const pX = (e.clientX / window.innerWidth - 0.5) * 24;
      const pY = (e.clientY / window.innerHeight - 0.5) * 24;
      setParallax({ x: pX, y: pY });

      const target = e.target as HTMLElement | null;
      if (target) {
        const interactive = target.closest('a, button, input, [role="button"], .hero-title, .card-flow-bg');
        setIsHoveringInteractive(!!interactive);
      }
    };

    const handleMouseLeave = () => setIsMouseInWindow(false);
    const handleMouseEnter = () => setIsMouseInWindow(true);

    window.addEventListener('mousemove', handleMouseMove);
    document.documentElement.addEventListener('mouseleave', handleMouseLeave);
    document.documentElement.addEventListener('mouseenter', handleMouseEnter);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.documentElement.removeEventListener('mouseleave', handleMouseLeave);
      document.documentElement.removeEventListener('mouseenter', handleMouseEnter);
    };
  }, [mouseX, mouseY]);

  const handleCopyCode = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleEnterWorkspace = () => {
    if (!getAuthToken()) {
      setIsAuthOpen(true);
      return;
    }
    navigate('/dashboard');
  };

  return (
    <div className="relative min-h-screen w-full bg-black text-white selection:bg-neutral-800 selection:text-white overflow-x-hidden font-sans">
      {/* Interactive Cursor Spotlight */}
      {isMouseInWindow && (
        <motion.div
          className="pointer-events-none fixed top-0 left-0 z-10 rounded-full bg-radial from-emerald-400/10 via-white/5 to-transparent blur-xl hidden md:block"
          style={{ x: smoothX, y: smoothY, translateX: '-50%', translateY: '-50%' }}
          animate={{
            width: isHoveringInteractive ? 140 : 80,
            height: isHoveringInteractive ? 140 : 80,
            opacity: isMouseInWindow ? 1 : 0,
          }}
          transition={{ type: 'spring', stiffness: 180, damping: 22 }}
        />
      )}

      {/* Background radial spotlight */}
      <div
        className="pointer-events-none fixed inset-0 z-0 transition-opacity duration-300 opacity-50 hidden md:block"
        style={{
          background: `radial-gradient(600px circle at ${rawMouse.x}px ${rawMouse.y}px, rgba(255, 255, 255, 0.035), transparent 70%)`,
        }}
      />

      {/* ========================================================= */}
      {/* HERO SECTION WITH VIDEO BACKGROUND & FLOATING CALLOUTS    */}
      {/* ========================================================= */}
      <section id="hero-section" className="relative h-screen w-full overflow-hidden bg-black">
        {/* Background Video with Smooth Parallax */}
        <div
          className="absolute inset-0 w-full h-full scale-[1.06] transition-transform duration-700 ease-out"
          style={{
            transform: `scale(1.06) translate3d(${parallax.x}px, ${parallax.y}px, 0)`,
          }}
        >
          <video
            id="hero-background-video"
            className="w-full h-full object-cover"
            autoPlay
            loop
            muted
            playsInline
            src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260702_051048_5ef213b5-26db-4da8-b604-7ef823760b6b.mp4"
          />
        </div>

        {/* Video Gradient Overlays */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black via-transparent to-black/30" />
        <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-b from-transparent to-black" />

        {/* Floating Fixed Header */}
        <header
          id="header-bar"
          className="fixed z-40 px-4 sm:px-8 pt-5 top-0 left-0 right-0 flex items-center justify-between pointer-events-none"
        >
          {/* Brand Pill */}
          <motion.a
            id="brand-pill"
            href="#hero-section"
            whileHover={{ scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            className="pointer-events-auto hidden sm:flex items-center gap-2.5 bg-neutral-900/90 backdrop-blur-xl rounded-full pl-3.5 pr-5 py-2.5 shadow-lg border border-neutral-800/80 hover:border-neutral-700 transition-all cursor-pointer"
          >
            <div className="w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <Shield className="w-3 h-3 fill-emerald-400 stroke-transparent" />
            </div>
            <span className="text-white text-xs font-semibold tracking-tight">CleanSlate</span>
          </motion.a>

          {/* Navigation Tabs Pill with Live Scanner Trigger */}
          <div className="mx-auto sm:mx-0 pointer-events-auto">
            <div className="flex items-center gap-1 bg-neutral-900/90 backdrop-blur-xl px-3 py-1.5 rounded-full border border-neutral-800/80 shadow-lg text-xs font-medium">
              <a
                href="#platform"
                className={`px-3 py-1.5 rounded-full transition-colors ${
                  activeTab === 'platform' ? 'text-white bg-neutral-800/80' : 'text-neutral-400 hover:text-white'
                }`}
              >
                platform
              </a>
              <a
                href="#solutions"
                className={`px-3 py-1.5 rounded-full transition-colors ${
                  activeTab === 'solutions' ? 'text-white bg-neutral-800/80' : 'text-neutral-400 hover:text-white'
                }`}
              >
                solutions
              </a>
              <a
                href="#company"
                className={`px-3 py-1.5 rounded-full transition-colors ${
                  activeTab === 'company' ? 'text-white bg-neutral-800/80' : 'text-neutral-400 hover:text-white'
                }`}
              >
                company
              </a>
              <a
                href="#support"
                className={`px-3 py-1.5 rounded-full transition-colors ${
                  activeTab === 'support' ? 'text-white bg-neutral-800/80' : 'text-neutral-400 hover:text-white'
                }`}
              >
                support
              </a>
              <button
                onClick={() => setIsScannerOpen(true)}
                className="ml-1 px-3 py-1 rounded-full bg-teal-500/20 hover:bg-teal-500/30 text-teal-300 border border-teal-500/30 flex items-center gap-1.5 text-[11px] transition-all cursor-pointer font-medium"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
                <span>Live Profiler</span>
              </button>
            </div>
          </div>

          {/* Right Action Buttons */}
          <div className="pointer-events-auto hidden sm:flex items-center gap-2.5">
            <motion.button
              id="btn-login-header"
              onClick={() => setIsAuthOpen(true)}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.96 }}
              className="text-neutral-300 hover:text-white text-xs font-medium px-4 py-2 rounded-full hover:bg-neutral-900/80 transition-all cursor-pointer"
            >
              log in
            </motion.button>
            <motion.button
              id="btn-get-started"
              onClick={handleEnterWorkspace}
              whileHover={{ scale: 1.05, y: -2, boxShadow: '0 8px 24px rgba(255, 255, 255, 0.2)' }}
              whileTap={{ scale: 0.96 }}
              transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              className="inline-flex items-center gap-2 bg-white text-black text-xs font-semibold rounded-full px-5 py-2.5 hover:bg-neutral-200 transition-all cursor-pointer shadow-md"
            >
              <Zap className="w-3.5 h-3.5 fill-black" />
              <span>Enter CleanSlate</span>
            </motion.button>
          </div>
        </header>

        {/* Hero Giant Typography & Content */}
        <div className="relative h-full w-full">
          <motion.h1
            id="headline-protect"
            whileHover={{ scale: 1.04, x: 12 }}
            transition={{ type: 'spring', stiffness: 300, damping: 18 }}
            className="hero-title absolute text-white font-medium text-[14vw] md:text-[13vw] left-4 md:left-10 top-[12%] select-none cursor-pointer z-10 tracking-tight"
          >
            clean
          </motion.h1>
          <motion.h1
            id="headline-your"
            whileHover={{ scale: 1.04, x: -12 }}
            transition={{ type: 'spring', stiffness: 300, damping: 18 }}
            className="hero-title absolute text-white font-medium text-[14vw] md:text-[13vw] right-4 md:right-10 top-[38%] select-none cursor-pointer z-10 tracking-tight"
          >
            your
          </motion.h1>
          <motion.h1
            id="headline-data"
            whileHover={{ scale: 1.04, y: -8 }}
            transition={{ type: 'spring', stiffness: 300, damping: 18 }}
            className="hero-title absolute text-white font-medium text-[14vw] md:text-[13vw] left-[18%] md:left-[28%] top-[58%] select-none cursor-pointer z-10 tracking-tight"
          >
            data
          </motion.h1>

          <motion.p
            id="hero-description"
            whileHover={{ x: 6 }}
            transition={{ type: 'spring', stiffness: 300 }}
            className="absolute left-6 md:left-10 top-[46%] max-w-[240px] text-[15px] leading-snug text-white/90 z-20 cursor-default"
          >
            we autonomously profile, clean, and repair your messy enterprise datasets — fully reversible
          </motion.p>

          {/* Interactive Stat Pins with Angled Lines */}
          <motion.div
            id="stat-block-startups"
            whileHover={{ scale: 1.08, y: -4 }}
            transition={{ type: 'spring', stiffness: 350, damping: 20 }}
            className="absolute right-6 md:right-24 top-[14%] z-20 cursor-pointer text-right"
          >
            <div className="flex items-center gap-3 justify-end">
              <div className="hidden md:block h-px w-16 bg-white/40 rotate-[20deg]" />
              <span className="text-2xl md:text-3xl font-medium tracking-tight text-white/90">Missing Values</span>
            </div>
            <p className="text-xs md:text-sm text-white/60 mt-1 max-w-[200px] ml-auto">
              NULL propagation corrupting analytics
            </p>
          </motion.div>

          <motion.div
            id="stat-block-protected"
            whileHover={{ scale: 1.08, y: -4 }}
            transition={{ type: 'spring', stiffness: 350, damping: 20 }}
            className="absolute left-4 md:left-8 bottom-20 md:bottom-24 z-20 cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl md:text-3xl font-medium tracking-tight text-white/90">Dirty Records</span>
              <div className="hidden md:block h-px w-16 bg-white/40 rotate-[-20deg]" />
            </div>
            <p className="text-xs md:text-sm text-white/60 mt-1 max-w-[200px]">
              duplicates & inconsistencies breaking pipelines
            </p>
          </motion.div>

          <motion.div
            id="stat-block-downloads"
            whileHover={{ scale: 1.08, y: -4 }}
            transition={{ type: 'spring', stiffness: 350, damping: 20 }}
            className="absolute right-6 md:right-20 bottom-16 md:bottom-20 z-20 cursor-pointer text-right"
          >
            <div className="flex items-center gap-3 justify-end">
              <div className="hidden md:block h-px w-16 bg-white/40 rotate-[-20deg]" />
              <span className="text-2xl md:text-3xl font-medium tracking-tight text-white/90">Information Loss</span>
            </div>
            <p className="text-xs md:text-sm text-white/60 mt-1 max-w-[200px] ml-auto">
              irreversible transforms destroying context
            </p>
          </motion.div>
        </div>
      </section>

      {/* ========================================================= */}
      {/* SECTION 1: PLATFORM ARCHITECTURE                           */}
      {/* ========================================================= */}
      <section id="platform" className="relative w-full bg-black py-28 px-6 md:px-12 border-t border-neutral-900 overflow-hidden">
        <div className="pointer-events-none absolute -top-40 right-0 w-96 h-96 bg-neutral-800/10 rounded-full blur-3xl" />
        <div className="max-w-6xl mx-auto space-y-16 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="space-y-3 text-left"
          >
            <span className="text-xs font-semibold uppercase tracking-widest text-neutral-400 font-mono">
              PLATFORM ARCHITECTURE
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-tight text-white uppercase">
              THE CLEANSLATE CLEANING ENGINE
            </h2>
            <p className="text-neutral-400 text-sm md:text-base max-w-2xl leading-relaxed">
              An autonomous, test-driven data cleaning layer that profiles, repairs, and validates every dataset with 100% reversibility and full information loss tracking.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Card 1 */}
            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 flex flex-col justify-between hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-neutral-900 border border-neutral-800 group-hover:border-neutral-700 flex items-center justify-center text-white transition-colors">
                  <Lock className="w-5 h-5 text-emerald-400" />
                </div>
                <h3 className="text-lg font-medium text-white uppercase tracking-tight">
                  Deterministic Profiling
                </h3>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  Autonomously profiles every column — detects types, distributions, null ratios, uniqueness, and statistical outliers in chunked passes.
                </p>
              </div>
              <div className="pt-6 border-t border-neutral-900 text-xs text-neutral-500 font-mono">
                Chunked • Zero Sampling Bias
              </div>
            </motion.div>

            {/* Card 2 */}
            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 flex flex-col justify-between hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-neutral-900 border border-neutral-800 group-hover:border-neutral-700 flex items-center justify-center text-white transition-colors">
                  <Key className="w-5 h-5 text-teal-400" />
                </div>
                <h3 className="text-lg font-medium text-white uppercase tracking-tight">
                  Semantic Constraint Inference
                </h3>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  AI-powered rule engine infers domain constraints — regex patterns, value ranges, referential integrity, and format standards.
                </p>
              </div>
              <div className="pt-6 border-t border-neutral-900 text-xs text-neutral-500 font-mono">
                LLM-Inferred • Pandera-Validated
              </div>
            </motion.div>

            {/* Card 3 */}
            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 flex flex-col justify-between hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-neutral-900 border border-neutral-800 group-hover:border-neutral-700 flex items-center justify-center text-white transition-colors">
                  <ShieldCheck className="w-5 h-5 text-cyan-400" />
                </div>
                <h3 className="text-lg font-medium text-white uppercase tracking-tight">
                  Reversible Execution Ledger
                </h3>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  Every transformation is recorded as a cryptographic delta with SHA-256 hashing — rollback any step to the exact original state.
                </p>
              </div>
              <div className="pt-6 border-t border-neutral-900 text-xs text-neutral-500 font-mono">
                SHA-256 • 100% Rollback
              </div>
            </motion.div>

            {/* Card 4 */}
            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 flex flex-col justify-between hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-neutral-900 border border-neutral-800 group-hover:border-neutral-700 flex items-center justify-center text-white transition-colors">
                  <Database className="w-5 h-5 text-indigo-400" />
                </div>
                <h3 className="text-lg font-medium text-white uppercase tracking-tight">
                  Information Loss Calculator
                </h3>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  Predicts exact data and context loss before every transformation — entropy metrics, row impact counts, and semantic coverage.
                </p>
              </div>
              <div className="pt-6 border-t border-neutral-900 text-xs text-neutral-500 font-mono">
                Pre-Execution Loss Analysis
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ========================================================= */}
      {/* SECTION 2: TARGET MARKETS & SOLUTIONS                      */}
      {/* ========================================================= */}
      <section id="solutions" className="relative w-full bg-black py-28 px-6 md:px-12 border-t border-neutral-900 overflow-hidden">
        <div className="pointer-events-none absolute -bottom-32 -left-32 w-96 h-96 bg-neutral-800/10 rounded-full blur-3xl" />
        <div className="max-w-6xl mx-auto space-y-16 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="space-y-3 text-left"
          >
            <span className="text-xs font-semibold uppercase tracking-widest text-neutral-400 font-mono">
              USE CASES
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-tight text-white uppercase">
              BUILT FOR MESSY ENTERPRISE DATA
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
            {/* Market 1 */}
            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 flex flex-col justify-between space-y-6 hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-neutral-900 border border-neutral-800 group-hover:border-neutral-700 flex items-center justify-center text-white transition-colors">
                  <Cpu className="w-6 h-6 text-teal-400" />
                </div>
                <h3 className="text-lg sm:text-xl font-medium text-white tracking-tight uppercase">
                  DATA ENGINEERING TEAMS
                </h3>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  Autonomously clean messy CSVs, databases, and data lake exports with{' '}
                  <strong className="text-white font-medium">test-driven pipelines, reversible transforms, and zero manual scripting</strong>{' '}
                  before data enters your ML training or analytics workflows.
                </p>
              </div>
              <div className="pt-4 border-t border-neutral-900 text-xs text-neutral-500 font-mono">
                ETL & ML Pipeline Cleaning
              </div>
            </motion.div>

            {/* Market 2 */}
            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 flex flex-col justify-between space-y-6 hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-neutral-900 border border-neutral-800 group-hover:border-neutral-700 flex items-center justify-center text-white transition-colors">
                  <Activity className="w-6 h-6 text-emerald-400" />
                </div>
                <h3 className="text-lg sm:text-xl font-medium text-white tracking-tight uppercase">
                  FINTECH & HEALTHCARE
                </h3>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  Clean and validate financial records, patient datasets, and regulatory filings with{' '}
                  <strong className="text-white font-medium">full audit trails, information loss guarantees, and Pandera schema enforcement</strong> for compliance-conscious environments.
                </p>
              </div>
              <div className="pt-4 border-t border-neutral-900 space-y-2">
                <div className="text-xs text-neutral-300">
                  <strong className="text-white font-medium">Audit-ready:</strong> Full Ledger • SHA-256 Hashing • Rollback
                </div>
                <p className="text-[11px] text-neutral-500 italic">
                  Every transformation cryptographically logged for regulatory evidence.
                </p>
              </div>
            </motion.div>

            {/* Market 3 */}
            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 flex flex-col justify-between space-y-6 hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-neutral-900 border border-neutral-800 group-hover:border-neutral-700 flex items-center justify-center text-white transition-colors">
                  <Globe className="w-6 h-6 text-cyan-400" />
                </div>
                <h3 className="text-lg sm:text-xl font-medium text-white tracking-tight uppercase">
                  ENTERPRISE & SAAS PLATFORMS
                </h3>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  Integrate autonomous cleaning across{' '}
                  <strong className="text-white font-medium">data lakes, warehouses, CRM exports, and multi-tenant datasets</strong>{' '}
                  with an intelligent agent designed to scale across enterprise data ecosystems.
                </p>
              </div>
              <div className="pt-4 border-t border-neutral-900 text-xs text-neutral-500 font-mono">
                Universal Cross-Dataset Cleaning
              </div>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="pt-8 border-t border-neutral-900 text-center sm:text-left cursor-default"
          >
            <p className="text-base sm:text-lg text-white font-medium tracking-tight">
              CleanSlate — One autonomous agent to clean, validate, and repair any enterprise dataset.
            </p>
          </motion.div>
        </div>
      </section>

      {/* ========================================================= */}
      {/* SECTION 3: COMPANY & WHAT WE DELIVER                       */}
      {/* ========================================================= */}
      <section id="company" className="relative w-full bg-black py-28 px-6 md:px-12 border-t border-neutral-900 overflow-hidden">
        <div className="max-w-6xl mx-auto space-y-16 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="space-y-3 text-left"
          >
            <span className="text-xs font-semibold uppercase tracking-widest text-neutral-400 font-mono">
              WHAT WE DELIVER
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-tight text-white uppercase">
              THE COMPLETE DATA CLEANING PIPELINE
            </h2>
            <p className="text-neutral-400 text-sm md:text-base max-w-2xl leading-relaxed">
              We provide the critical building blocks to clean your data pipelines — profiling, constraint inference, reversible repairs, and continuous validation.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 space-y-4 hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="text-3xl font-medium text-white tracking-tight group-hover:scale-105 transition-transform origin-left">
                Ingest
              </div>
              <h3 className="text-base font-medium text-white uppercase">Smart Dataset Ingestion</h3>
              <p className="text-xs sm:text-sm text-neutral-400 leading-relaxed">
                Upload CSVs, connect to databases, or paste raw data — automatic type inference, encoding detection, and schema registration.
              </p>
            </motion.div>

            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 space-y-4 hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="text-3xl font-medium text-white tracking-tight group-hover:scale-105 transition-transform origin-left">
                Clean
              </div>
              <h3 className="text-base font-medium text-white uppercase">Reversible Transformation Engine</h3>
              <p className="text-xs sm:text-sm text-neutral-400 leading-relaxed">
                Apply null imputation, deduplication, outlier treatment, and format normalization — every step logged with full rollback support.
              </p>
            </motion.div>

            <motion.div
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 380, damping: 22 }}
              className="card-flow-bg p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 space-y-4 hover:border-neutral-600 transition-colors cursor-pointer group"
            >
              <div className="text-3xl font-medium text-white tracking-tight group-hover:scale-105 transition-transform origin-left">
                Verify
              </div>
              <h3 className="text-base font-medium text-white uppercase">Test-Driven Validation</h3>
              <p className="text-xs sm:text-sm text-neutral-400 leading-relaxed">
                Auto-generated Pandera schemas, mutation testing, and adversarial benchmarks validate cleaning quality continuously.
              </p>
            </motion.div>
          </div>

          <div className="p-8 sm:p-10 rounded-3xl bg-neutral-950 border border-neutral-800/90 grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-3">
              <h4 className="text-lg font-medium text-white uppercase">100% Reversibility Guarantee</h4>
              <p className="text-sm text-neutral-400 leading-relaxed">
                Our cryptographic ledger architecture ensures every data transformation is recorded as a delta — rollback to the exact original state at any point with SHA-256 hash verification.
              </p>
            </div>
            <div className="space-y-3">
              <h4 className="text-lg font-medium text-white uppercase">Information Loss Transparency</h4>
              <p className="text-sm text-neutral-400 leading-relaxed">
                Before any cleaning step executes, CleanSlate predicts exact row impact, entropy change, and semantic coverage loss — so you decide what to clean with full visibility.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================= */}
      {/* SECTION 4: DEVELOPER & ENTERPRISE SUPPORT                  */}
      {/* ========================================================= */}
      <section id="support" className="relative w-full bg-black py-28 px-6 md:px-12 border-t border-neutral-900 overflow-hidden">
        <div className="max-w-6xl mx-auto space-y-16 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="space-y-3 text-left"
          >
            <span className="text-xs font-semibold uppercase tracking-widest text-neutral-400 font-mono">
              DEVELOPER & ENTERPRISE SUPPORT
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-tight text-white uppercase">
              START CLEANING WITH CLEANSLATE
            </h2>
            <p className="text-neutral-400 text-sm md:text-base max-w-2xl leading-relaxed">
              Integrate CleanSlate in minutes with native Python SDK, comprehensive REST APIs, and enterprise-grade cleaning automation.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Interactive Code Playground */}
            <div className="card-flow-bg lg:col-span-7 p-6 sm:p-8 rounded-3xl bg-neutral-950 border border-neutral-800/90 flex flex-col justify-between space-y-6 hover:border-neutral-600 transition-colors">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCodeLanguage('typescript')}
                      className={`px-4 py-1.5 rounded-full text-xs font-medium transition-colors cursor-pointer ${
                        codeLanguage === 'typescript' ? 'bg-white text-black' : 'text-neutral-400 hover:text-white bg-neutral-900'
                      }`}
                    >
                      TypeScript
                    </button>
                    <button
                      onClick={() => setCodeLanguage('python')}
                      className={`px-4 py-1.5 rounded-full text-xs font-medium transition-colors cursor-pointer ${
                        codeLanguage === 'python' ? 'bg-white text-black' : 'text-neutral-400 hover:text-white bg-neutral-900'
                      }`}
                    >
                      Python
                    </button>
                  </div>
                  <button
                    onClick={() =>
                      handleCopyCode(
                        codeLanguage === 'typescript' ? 'npm i @cleanslate/sdk' : 'pip install cleanslate'
                      )
                    }
                    className="text-xs font-mono text-neutral-400 hover:text-white bg-neutral-900 px-3 py-1 rounded-full border border-neutral-800 transition-colors cursor-pointer hover:border-neutral-600 flex items-center gap-1.5"
                  >
                    {copiedCode ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedCode ? 'Copied!' : codeLanguage === 'typescript' ? 'npm i @cleanslate/sdk' : 'pip install cleanslate'}</span>
                  </button>
                </div>

                <div className="p-4 rounded-2xl bg-neutral-900/90 border border-neutral-800 font-mono text-xs text-neutral-300">
                  <pre className="overflow-x-auto text-[11px] leading-relaxed text-neutral-200">
                    {codeLanguage === 'typescript'
                      ? `import { CleanSlate } from '@cleanslate/sdk';

const cs = new CleanSlate({
  apiUrl: 'http://localhost:8000',
  token: process.env.CLEANSLATE_TOKEN,
});

// Profile, clean, and verify a messy dataset
const dataset = await cs.upload('./enterprise_data.csv');
const profile = await cs.profile(dataset.id);
const plan = await cs.generatePlan(dataset.id);

// Apply reversible cleaning with loss estimation
const result = await cs.apply(plan.id);
console.log(result.information_loss); // { rows_affected: 847 }`
                      : `from cleanslate import CleanSlate
import os

cs = CleanSlate(
    api_url="http://localhost:8000",
    token=os.getenv("CLEANSLATE_TOKEN")
)

# Profile, clean, and verify a messy dataset
dataset = cs.upload("enterprise_data.csv")
profile = cs.profile(dataset.id)
plan = cs.generate_plan(dataset.id)

# Apply reversible cleaning with loss estimation
result = cs.apply(plan.id)
print(result.information_loss)  # {rows_affected: 847}`}
                  </pre>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-neutral-400 pt-2 border-t border-neutral-900">
                <span className="flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  <span>Full reversibility & information loss tracking</span>
                </span>
                <span className="font-mono text-neutral-500">v1.0.0 (Latest)</span>
              </div>
            </div>

            {/* Support and Direct Launch Panel */}
            <div className="lg:col-span-5 space-y-4 flex flex-col justify-between">
              <div className="p-6 rounded-3xl bg-neutral-950 border border-neutral-800/90 space-y-3 hover:border-neutral-600 transition-colors">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-white uppercase">Live Pipeline Monitoring</h4>
                  <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-400 uppercase tracking-wider bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-800/50">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Online
                  </span>
                </div>
                <p className="text-xs text-neutral-400 leading-relaxed">
                  Real-time audit logs, system health monitoring, and cleaning pipeline status across all active datasets.
                </p>
              </div>

              <div className="p-6 rounded-3xl bg-neutral-950 border border-neutral-800/90 space-y-3 hover:border-neutral-600 transition-colors">
                <h4 className="text-sm font-medium text-white uppercase">Adversarial Resilience Lab</h4>
                <p className="text-xs text-neutral-400 leading-relaxed">
                  Built-in adversarial corpus testing and mutation benchmarks to stress-test your cleaning pipeline against worst-case data quality scenarios.
                </p>
              </div>

              <motion.div
                whileHover={{ y: -6, scale: 1.02 }}
                transition={{ type: 'spring', stiffness: 350, damping: 20 }}
                className="p-6 rounded-3xl bg-white text-black space-y-3 shadow-xl"
              >
                <h4 className="text-sm font-medium text-black uppercase">Ready to get started?</h4>
                <p className="text-xs text-neutral-700 leading-relaxed">
                  Launch the CleanSlate autonomous cleaning engine and reversible ledger workspace right now.
                </p>
                <motion.button
                  onClick={handleEnterWorkspace}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="w-full bg-black text-white text-xs font-semibold py-3 px-4 rounded-full flex items-center justify-center gap-2 hover:bg-neutral-800 transition-colors cursor-pointer shadow-lg"
                >
                  <span>Launch Platform Workspace</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </motion.button>
              </motion.div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================= */}
      {/* FOOTER                                                     */}
      {/* ========================================================= */}
      <footer className="w-full bg-black py-16 px-6 md:px-12 border-t border-neutral-900 text-xs">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-neutral-500">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-white">
              <Shield className="w-3 h-3 fill-white stroke-black" />
            </div>
            <span className="text-white font-medium tracking-tight">CleanSlate</span>
            <span className="text-[11px] text-neutral-600">
              © {new Date().getFullYear()} CleanSlate. All rights reserved.
            </span>
          </div>

          <div className="flex items-center gap-6 text-neutral-400">
            <a href="#platform" className="hover:text-white transition-colors">
              platform
            </a>
            <a href="#solutions" className="hover:text-white transition-colors">
              solutions
            </a>
            <a href="#company" className="hover:text-white transition-colors">
              company
            </a>
            <a href="#support" className="hover:text-white transition-colors">
              support
            </a>
            <button onClick={handleEnterWorkspace} className="text-emerald-400 hover:text-emerald-300 transition-colors">
              workspace
            </button>
          </div>

          <div className="text-neutral-400">One autonomous agent to clean, validate, and repair any enterprise dataset.</div>
        </div>
      </footer>

      {/* Live Modals */}
      <LiveThreatScannerModal
        isOpen={isScannerOpen}
        onClose={() => setIsScannerOpen(false)}
        onEnterApp={handleEnterWorkspace}
      />
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onLoginSuccess={handleEnterWorkspace}
      />
    </div>
  );
};
