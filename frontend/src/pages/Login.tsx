import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiRequest, setAuthToken } from '../api/client';
import { Sparkles, ArrowRight, ShieldCheck, Lock, Shield } from 'lucide-react';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@cleanslate.local');
  const [password, setPassword] = useState('cleanslate123!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Try login first
      const resp = await apiRequest<{ access_token: string; token_type: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setAuthToken(resp.access_token);
      navigate('/dashboard');
    } catch {
      // If failed, try register then login
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
        navigate('/dashboard');
      } catch (err2: any) {
        setError(err2.message || 'Authentication failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemo = async () => {
    setEmail('admin@cleanslate.local');
    setPassword('cleanslate123!');
    setLoading(true);
    setError(null);
    try {
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
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Demo login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-6 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-slate-900/90 border border-slate-800 rounded-2xl p-8 backdrop-blur-xl shadow-2xl relative z-10">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/25">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">CleanSlate</h1>
            <p className="text-xs text-slate-400">Autonomous Enterprise Data Cleaning</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/80 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700/80 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
          >
            {loading ? (
              <span className="animate-pulse">Authenticating...</span>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-800" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-slate-900 px-2 text-slate-500 font-semibold tracking-wider">or instant demo</span>
          </div>
        </div>

        <button
          onClick={handleQuickDemo}
          disabled={loading}
          className="w-full py-2.5 px-4 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-cyan-400 border border-slate-700/80 font-medium text-sm flex items-center justify-center gap-2 transition-all cursor-pointer"
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Launch As Demo Admin</span>
        </button>

        <div className="mt-4 text-center">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-emerald-400 transition-colors"
          >
            <Shield className="w-3.5 h-3.5" />
            <span>← Return to ShieldSense Landing Page</span>
          </Link>
        </div>

        <div className="mt-6 flex items-center justify-between text-[11px] text-slate-500 pt-4 border-t border-slate-800/80">
          <span className="flex items-center gap-1">
            <Lock className="w-3 h-3" /> Reversible Ledger v1.0
          </span>
          <span>Zero HTTP 500 Guarantee</span>
        </div>
      </div>
    </div>
  );
};
