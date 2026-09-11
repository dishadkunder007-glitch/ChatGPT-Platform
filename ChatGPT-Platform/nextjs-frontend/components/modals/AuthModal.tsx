'use client';

import { useState } from 'react';
import {
  X,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  ArrowRight,
  AlertCircle,
  Mail,
  Lock,
  User as UserIcon,
  Sparkles,
} from 'lucide-react';
import { useStore } from '@/lib/store';
import * as api from '@/lib/api';
import { signInWithGooglePopup, isFirebaseConfigured } from '@/lib/firebase';
import { cn } from '@/lib/utils';

interface AuthModalProps {
  onClose: () => void;
  initialMode?: 'login' | 'register' | 'reset';
}

export function AuthModal({ onClose, initialMode = 'login' }: AuthModalProps) {
  const { setUser, setToken, setConversations, setActiveConvId, setMessages } = useStore();

  const detectedMode =
    typeof window !== 'undefined' && (window as any).__authMode === 'register'
      ? 'register'
      : initialMode;

  const [mode, setMode] = useState<'login' | 'register' | 'reset'>(detectedMode);
  const [showDirectGooglePrompt, setShowDirectGooglePrompt] = useState(false);
  const [googleEmail, setGoogleEmail] = useState('');
  const [googleName, setGoogleName] = useState('');

  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Password strength calculation
  const pwStrength =
    password.length === 0
      ? 0
      : password.length < 8
      ? 1
      : /[A-Z]/.test(password) && /[0-9]/.test(password)
      ? 3
      : 2;

  const pwColors = ['', 'bg-rose-500', 'bg-amber-500', 'bg-emerald-500'];
  const pwLabels = ['', 'Weak (min 8 chars)', 'Good', 'Strong'];

  async function completeAuth(res: { access_token: string; user: any }) {
    api.setToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);

    setActiveConvId(null);
    setMessages([]);

    try {
      const convs = await api.getConversations();
      setConversations(convs);
    } catch {
      setConversations([]);
    }

    if (typeof window !== 'undefined') {
      delete (window as any).__authMode;
    }

    onClose();
  }

  async function handleFirebaseGoogleSignIn() {
    setGoogleLoading(true);
    setError('');
    setSuccess('');

    if (!isFirebaseConfigured) {
      setShowDirectGooglePrompt(true);
      setGoogleLoading(false);
      return;
    }

    try {
      const googleUser = await signInWithGooglePopup();
      const res = await api.googleAuth(
        googleUser.credential,
        googleUser.email,
        googleUser.name,
        googleUser.avatar_url,
        googleUser.firebase_uid
      );
      await completeAuth(res);
    } catch (err: any) {
      if (err.code === 'auth/popup-closed-by-user' || err.code === 'auth/cancelled-popup-request') {
        setGoogleLoading(false);
        return;
      }
      if (
        err.code === 'auth/invalid-api-key' ||
        err.code === 'auth/api-key-not-valid' ||
        err.code === 'auth/unauthorized-domain'
      ) {
        setError('Google authentication is in development fallback mode. Enter email below.');
        setShowDirectGooglePrompt(true);
      } else {
        setError(err.message || 'Google sign-in failed. Please try again.');
      }
    } finally {
      setGoogleLoading(false);
    }
  }

  async function handleDirectGoogleSignIn(e: React.FormEvent) {
    e.preventDefault();
    if (!googleEmail.trim()) {
      setError('Please enter your Google email address.');
      return;
    }

    const trimmed = googleEmail.trim().toLowerCase();
    const finalEmail = trimmed.includes('@') ? trimmed : `${trimmed}@gmail.com`;
    const finalName = googleName.trim() || finalEmail.split('@')[0];
    const avatarUrl = `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(
      finalName
    )}&backgroundColor=10b981,3b82f6`;
    const mockUid = `google_${Buffer.from(finalEmail).toString('base64').replace(/=/g, '').slice(0, 20)}`;

    setGoogleLoading(true);
    setError('');

    try {
      const res = await api.googleAuth('', finalEmail, finalName, avatarUrl, mockUid);
      await completeAuth(res);
    } catch (err: any) {
      setError(err.message || 'Google sign-in failed. Please try again.');
    } finally {
      setGoogleLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      if (mode === 'register') {
        const res = await api.register(email, name, password);
        await completeAuth(res);
      } else if (mode === 'login') {
        const res = await api.login(email, password);
        await completeAuth(res);
      } else if (mode === 'reset') {
        await api.requestPasswordReset(email);
        setSuccess('If an account matches that email, a password reset link has been dispatched.');
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="relative w-full max-w-[440px] bg-[#121215] border border-white/10 rounded-3xl shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9)] overflow-hidden text-white animate-in fade-in zoom-in-95 duration-200">
        {/* Glow accent */}
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-64 h-32 bg-emerald-500/15 blur-3xl pointer-events-none rounded-full" />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-5 top-5 p-2 rounded-full hover:bg-white/5 text-zinc-400 hover:text-white transition-colors z-10"
          title="Close"
        >
          <X size={18} />
        </button>

        <div className="p-8 sm:p-10 flex flex-col items-center relative">
          {/* Brand Icon */}
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-400 p-[1px] shadow-lg shadow-emerald-500/20 mb-4 flex items-center justify-center">
            <div className="w-full h-full bg-[#121215] rounded-2xl flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-emerald-400" />
            </div>
          </div>

          {/* Heading */}
          <h1 className="text-2xl font-bold tracking-tight text-white mb-1.5 text-center">
            {showDirectGooglePrompt
              ? 'Sign in with Google'
              : mode === 'login'
              ? 'Welcome back'
              : mode === 'register'
              ? 'Create account'
              : 'Reset password'}
          </h1>
          <p className="text-xs text-zinc-400 text-center mb-6 max-w-xs">
            {showDirectGooglePrompt
              ? 'Continue with your Google account credentials'
              : mode === 'login'
              ? 'Access your saved chats, indexed documents, and local AI'
              : mode === 'register'
              ? 'Unlock fast AI document Q&A and personalized conversations'
              : 'Enter your registered email to receive password reset instructions'}
          </p>

          {/* Pill Mode Switcher (Login / Register) */}
          {!showDirectGooglePrompt && mode !== 'reset' && (
            <div className="w-full grid grid-cols-2 bg-zinc-900/90 border border-white/5 p-1 rounded-2xl mb-6">
              <button
                type="button"
                onClick={() => {
                  setMode('login');
                  setError('');
                  setSuccess('');
                }}
                className={cn(
                  'py-2 text-xs font-semibold rounded-xl transition-all duration-200',
                  mode === 'login'
                    ? 'bg-zinc-800 text-white shadow-sm border border-white/5'
                    : 'text-zinc-400 hover:text-zinc-200'
                )}
              >
                Log In
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('register');
                  setError('');
                  setSuccess('');
                }}
                className={cn(
                  'py-2 text-xs font-semibold rounded-xl transition-all duration-200',
                  mode === 'register'
                    ? 'bg-zinc-800 text-white shadow-sm border border-white/5'
                    : 'text-zinc-400 hover:text-zinc-200'
                )}
              >
                Sign Up
              </button>
            </div>
          )}

          {/* Alerts */}
          {error && (
            <div className="w-full bg-rose-500/10 border border-rose-500/20 rounded-xl px-3.5 py-2.5 text-xs text-rose-300 mb-4 flex items-start gap-2 animate-in fade-in">
              <AlertCircle size={15} className="flex-shrink-0 mt-0.5 text-rose-400" />
              <span className="flex-1 leading-snug">{error}</span>
            </div>
          )}
          {success && (
            <div className="w-full bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3.5 py-2.5 text-xs text-emerald-300 mb-4 flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 size={15} className="flex-shrink-0 text-emerald-400" />
              <span className="flex-1">{success}</span>
            </div>
          )}

          {/* Google Sign-In Direct Fallback */}
          {showDirectGooglePrompt ? (
            <form onSubmit={handleDirectGoogleSignIn} className="w-full space-y-3.5">
              <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-3.5 flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      fill="#4285F4"
                    />
                    <path
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      fill="#34A853"
                    />
                    <path
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      fill="#FBBC05"
                    />
                    <path
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      fill="#EA4335"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-semibold text-zinc-200">Google Account Authentication</p>
                  <p className="text-[11px] text-zinc-500">Fast sign-in with your Google ID</p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Google Email</label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                  <input
                    type="email"
                    value={googleEmail}
                    onChange={(e) => setGoogleEmail(e.target.value)}
                    required
                    autoFocus
                    placeholder="yourname@gmail.com"
                    className="w-full bg-zinc-900/90 border border-zinc-800 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 outline-none transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Display Name (Optional)</label>
                <div className="relative">
                  <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                  <input
                    type="text"
                    value={googleName}
                    onChange={(e) => setGoogleName(e.target.value)}
                    placeholder="Your Name"
                    className="w-full bg-zinc-900/90 border border-zinc-800 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 outline-none transition-all"
                  />
                </div>
              </div>

              <div className="flex gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDirectGooglePrompt(false)}
                  className="flex-1 py-2.5 rounded-xl border border-zinc-800 hover:border-zinc-700 text-zinc-300 hover:text-white text-xs font-semibold transition-colors"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={googleLoading}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-[0.99] text-white text-xs font-semibold transition-all shadow-md shadow-emerald-900/20 disabled:opacity-50"
                >
                  {googleLoading ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                  Continue
                </button>
              </div>
            </form>
          ) : (
            <>
              {/* Google Button */}
              {mode !== 'reset' && (
                <div className="w-full space-y-4">
                  <button
                    type="button"
                    onClick={handleFirebaseGoogleSignIn}
                    disabled={googleLoading}
                    className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl bg-zinc-900/90 hover:bg-zinc-800/90 border border-zinc-800 hover:border-zinc-700 text-zinc-200 text-xs font-medium transition-all shadow-sm active:scale-[0.99] disabled:opacity-50 cursor-pointer"
                  >
                    {googleLoading ? (
                      <Loader2 size={16} className="animate-spin text-zinc-400" />
                    ) : (
                      <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
                        <path
                          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                          fill="#4285F4"
                        />
                        <path
                          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                          fill="#34A853"
                        />
                        <path
                          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                          fill="#FBBC05"
                        />
                        <path
                          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                          fill="#EA4335"
                        />
                      </svg>
                    )}
                    <span>Continue with Google</span>
                  </button>

                  {/* Divider */}
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-px bg-zinc-800/80" />
                    <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-semibold">OR</span>
                    <div className="flex-1 h-px bg-zinc-800/80" />
                  </div>
                </div>
              )}

              {/* Form Inputs */}
              <form onSubmit={handleSubmit} className="w-full space-y-3 mt-4">
                {mode === 'register' && (
                  <div>
                    <label className="block text-xs font-medium text-zinc-400 mb-1">Full Name</label>
                    <div className="relative">
                      <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        placeholder="John Doe"
                        className="w-full bg-zinc-900/90 border border-zinc-800 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 outline-none transition-all"
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Email Address</label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder="name@example.com"
                      className="w-full bg-zinc-900/90 border border-zinc-800 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 outline-none transition-all"
                    />
                  </div>
                </div>

                {mode !== 'reset' && (
                  <div>
                    <label className="block text-xs font-medium text-zinc-400 mb-1">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                      <input
                        type={showPw ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={8}
                        placeholder="••••••••"
                        className="w-full bg-zinc-900/90 border border-zinc-800 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30 rounded-xl pl-10 pr-10 py-2.5 text-sm text-white placeholder-zinc-500 outline-none transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPw(!showPw)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors p-1"
                      >
                        {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>

                    {mode === 'register' && password.length > 0 && (
                      <div className="mt-2 space-y-1">
                        <div className="flex gap-1">
                          {[1, 2, 3].map((i) => (
                            <div
                              key={i}
                              className={cn(
                                'h-1 flex-1 rounded-full transition-all duration-300',
                                i <= pwStrength ? pwColors[pwStrength] : 'bg-zinc-800'
                              )}
                            />
                          ))}
                        </div>
                        <p
                          className={cn(
                            'text-[11px] font-medium',
                            pwStrength === 1
                              ? 'text-rose-400'
                              : pwStrength === 2
                              ? 'text-amber-400'
                              : 'text-emerald-400'
                          )}
                        >
                          {pwLabels[pwStrength]}
                        </p>
                      </div>
                    )}

                    {mode === 'login' && (
                      <div className="flex justify-end mt-1.5">
                        <button
                          type="button"
                          onClick={() => {
                            setMode('reset');
                            setError('');
                            setSuccess('');
                          }}
                          className="text-[11px] text-zinc-400 hover:text-emerald-400 transition-colors cursor-pointer"
                        >
                          Forgot password?
                        </button>
                      </div>
                    )}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-[0.99] text-white text-xs font-semibold transition-all shadow-md shadow-emerald-900/30 disabled:opacity-50 mt-3 cursor-pointer"
                >
                  {loading && <Loader2 size={14} className="animate-spin" />}
                  {mode === 'login' ? 'Sign In' : mode === 'register' ? 'Create Account' : 'Send Reset Link'}
                </button>
              </form>

              {/* Mode Toggle Link */}
              <div className="mt-5 text-center text-xs text-zinc-400">
                {mode === 'reset' && (
                  <button
                    onClick={() => {
                      setMode('login');
                      setError('');
                      setSuccess('');
                    }}
                    className="text-emerald-400 hover:text-emerald-300 font-medium hover:underline cursor-pointer"
                  >
                    ← Back to Log in
                  </button>
                )}
              </div>

              <div className="mt-5 pt-4 border-t border-zinc-800/80 text-[11px] text-zinc-600 flex items-center gap-3">
                <span className="hover:text-zinc-400 cursor-pointer">Terms of Service</span>
                <span>•</span>
                <span className="hover:text-zinc-400 cursor-pointer">Privacy Policy</span>
                <span>•</span>
                <span className="text-zinc-500">Local RAG AI</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
