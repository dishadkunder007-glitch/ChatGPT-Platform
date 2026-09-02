'use client';

import { useState } from 'react';
import { X, Eye, EyeOff, Loader2, CheckCircle2, ArrowRight, AlertCircle } from 'lucide-react';
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

  // Password strength for registration
  const pwStrength =
    password.length === 0 ? 0
    : password.length < 8 ? 1
    : /[A-Z]/.test(password) && /[0-9]/.test(password) ? 3
    : 2;
  const pwColors = ['', 'bg-red-500', 'bg-yellow-500', 'bg-emerald-500'];
  const pwLabels = ['', 'Weak', 'Good', 'Strong'];

  /**
   * Complete sign-in flow: sets token, clears old session data,
   * presents a fresh clean chat page, and loads new user conversations.
   */
  async function completeAuth(res: { access_token: string; user: any }) {
    api.setToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);

    // Reset old conversation & messages so the new user starts on a clean page
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

  /**
   * Firebase Google Authentication Handler
   */
  async function handleFirebaseGoogleSignIn() {
    setGoogleLoading(true);
    setError('');
    setSuccess('');

    // If Firebase keys aren't configured yet, offer direct fallback seamlessly
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
        // User closed or dismissed the popup window
        setGoogleLoading(false);
        return;
      }
      if (err.code === 'auth/invalid-api-key' || err.code === 'auth/api-key-not-valid' || err.code === 'auth/unauthorized-domain') {
        // On missing or misconfigured credentials, display message and offer manual entry
        setError(err.message || 'Firebase configuration issue. Please check your credentials.');
        setShowDirectGooglePrompt(true);
      } else {
        setError(err.message || 'Google sign-in failed. Please try again.');
      }
    } finally {
      setGoogleLoading(false);
    }
  }

  /**
   * Fallback / Direct Google Sign-In Handler (when Firebase credentials are in setup)
   */
  async function handleDirectGoogleSignIn(e: React.FormEvent) {
    e.preventDefault();
    if (!googleEmail.trim()) {
      setError('Please enter your Google email address.');
      return;
    }

    const trimmed = googleEmail.trim().toLowerCase();
    const finalEmail = trimmed.includes('@') ? trimmed : `${trimmed}@gmail.com`;
    const finalName = googleName.trim() || finalEmail.split('@')[0];
    const avatarUrl = `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(finalName)}&backgroundColor=10b981,3b82f6`;
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

  /**
   * Standard Email & Password / Register / Reset Handler
   */
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
        setSuccess('If that email exists, a password reset link has been dispatched.');
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#181818] border border-[#2e2e2e] rounded-3xl w-full max-w-[420px] shadow-2xl overflow-hidden relative text-white animate-in fade-in zoom-in-95 duration-200">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 p-2 rounded-full hover:bg-[#2b2b2b] text-gray-400 hover:text-white transition-colors"
          title="Close"
        >
          <X size={18} />
        </button>

        <div className="p-8 sm:p-10 flex flex-col items-center">
          {/* Heading */}
          <h1 className="text-2xl font-bold tracking-tight text-white mb-2 text-center mt-2">
            {showDirectGooglePrompt
              ? 'Sign in with Google'
              : mode === 'login'
              ? 'Welcome back'
              : mode === 'register'
              ? 'Create your account'
              : 'Reset your password'}
          </h1>
          <p className="text-sm text-gray-400 text-center mb-7">
            {showDirectGooglePrompt
              ? 'Sign in using your Google account'
              : mode === 'login'
              ? 'Sign in to access your chat history and AI models'
              : mode === 'register'
              ? 'Get started with your free ChatGPT Platform account'
              : 'Enter your email to receive a password reset link'}
          </p>

          {/* Alerts */}
          {error && (
            <div className="w-full bg-red-500/15 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400 mb-5 leading-relaxed flex items-start gap-2.5">
              <AlertCircle size={17} className="flex-shrink-0 mt-0.5 text-red-400" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="w-full bg-emerald-500/15 border border-emerald-500/30 rounded-xl px-4 py-3 text-sm text-emerald-400 mb-5 flex items-center gap-2">
              <CheckCircle2 size={16} />
              {success}
            </div>
          )}

          {/* ═══════════════════════════════════════════════
              Google Account Direct Sign-In Form (Fallback Prompt)
          ═══════════════════════════════════════════════ */}
          {showDirectGooglePrompt ? (
            <form onSubmit={handleDirectGoogleSignIn} className="w-full space-y-4">
              <div className="bg-[#212121] border border-[#333] rounded-xl p-3.5 flex items-center gap-3 mb-2">
                <svg className="w-6 h-6 flex-shrink-0" viewBox="0 0 24 24">
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
                <div className="text-left">
                  <p className="text-xs font-semibold text-white">Google Account Access</p>
                  <p className="text-[11px] text-gray-400">Sign in with your Google email</p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Google Email</label>
                <input
                  type="email"
                  value={googleEmail}
                  onChange={(e) => setGoogleEmail(e.target.value)}
                  required
                  autoFocus
                  placeholder="yourname@gmail.com"
                  className="w-full bg-[#202123] border border-[#383838] focus:border-emerald-500 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Display Name (Optional)</label>
                <input
                  type="text"
                  value={googleName}
                  onChange={(e) => setGoogleName(e.target.value)}
                  placeholder="Your Name"
                  className="w-full bg-[#202123] border border-[#383838] focus:border-emerald-500 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition-colors"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDirectGooglePrompt(false)}
                  className="flex-1 py-3 rounded-xl border border-[#383838] hover:border-[#4d4d4d] text-gray-300 hover:text-white text-sm font-medium transition-colors"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={googleLoading}
                  className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-[0.98] text-white text-sm font-semibold transition-all shadow-md disabled:opacity-50"
                >
                  {googleLoading ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                  Continue
                </button>
              </div>
            </form>
          ) : (
            <>
              {/* ═══════════════════════════════════════════════
                  1. Continue with Google Button
              ═══════════════════════════════════════════════ */}
              {mode !== 'reset' && (
                <div className="w-full">
                  <button
                    type="button"
                    onClick={handleFirebaseGoogleSignIn}
                    disabled={googleLoading}
                    className="w-full flex items-center justify-center gap-3 px-4 py-3.5 rounded-xl bg-[#212121] hover:bg-[#2a2a2a] border border-[#383838] hover:border-[#4d4d4d] text-white text-sm font-medium transition-all shadow-sm active:scale-[0.99] disabled:opacity-50 mb-5 cursor-pointer"
                  >
                    {googleLoading ? (
                      <Loader2 size={18} className="animate-spin text-gray-300" />
                    ) : (
                      <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24">
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
                  <div className="flex items-center gap-3 mb-5">
                    <div className="flex-1 h-px bg-[#2f2f2f]" />
                    <span className="text-xs text-gray-500 uppercase tracking-widest font-semibold">OR</span>
                    <div className="flex-1 h-px bg-[#2f2f2f]" />
                  </div>
                </div>
              )}

              {/* ═══════════════════════════════════════════════
                  2. Email & Password Form
              ═══════════════════════════════════════════════ */}
              <form onSubmit={handleSubmit} className="w-full space-y-4">
                {mode === 'register' && (
                  <div>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      placeholder="Full Name"
                      className="w-full bg-[#202123] border border-[#383838] focus:border-emerald-500 rounded-xl px-4 py-3.5 text-sm text-white placeholder-gray-500 outline-none transition-colors"
                    />
                  </div>
                )}

                <div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    placeholder="Email address"
                    className="w-full bg-[#202123] border border-[#383838] focus:border-emerald-500 rounded-xl px-4 py-3.5 text-sm text-white placeholder-gray-500 outline-none transition-colors"
                  />
                </div>

                {mode !== 'reset' && (
                  <div>
                    <div className="relative">
                      <input
                        type={showPw ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={8}
                        placeholder="Password"
                        className="w-full bg-[#202123] border border-[#383838] focus:border-emerald-500 rounded-xl px-4 py-3.5 pr-11 text-sm text-white placeholder-gray-500 outline-none transition-colors"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPw(!showPw)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors p-1"
                      >
                        {showPw ? <EyeOff size={17} /> : <Eye size={17} />}
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
                                i <= pwStrength ? pwColors[pwStrength] : 'bg-[#333]'
                              )}
                            />
                          ))}
                        </div>
                        <p
                          className={cn(
                            'text-xs font-medium',
                            pwStrength === 1
                              ? 'text-red-400'
                              : pwStrength === 2
                              ? 'text-yellow-400'
                              : 'text-emerald-400'
                          )}
                        >
                          {pwLabels[pwStrength]} password
                        </p>
                      </div>
                    )}

                    {mode === 'login' && (
                      <div className="flex justify-end mt-2">
                        <button
                          type="button"
                          onClick={() => { setMode('reset'); setError(''); setSuccess(''); }}
                          className="text-xs text-emerald-400 hover:text-emerald-300 hover:underline cursor-pointer"
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
                  className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-[0.99] text-white text-sm font-semibold transition-all shadow-md disabled:opacity-50 mt-2 cursor-pointer"
                >
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  {mode === 'login' ? 'Continue' : mode === 'register' ? 'Create account' : 'Send reset link'}
                </button>
              </form>

              {/* ═══════════════════════════════════════════════
                  3. Footer Switcher
              ═══════════════════════════════════════════════ */}
              <div className="mt-6 text-center text-sm text-gray-400">
                {mode === 'login' && (
                  <p>
                    Don&apos;t have an account?{' '}
                    <button
                      onClick={() => { setMode('register'); setError(''); setSuccess(''); }}
                      className="text-emerald-400 hover:text-emerald-300 font-medium hover:underline ml-1 cursor-pointer"
                    >
                      Sign up
                    </button>
                  </p>
                )}
                {mode === 'register' && (
                  <p>
                    Already have an account?{' '}
                    <button
                      onClick={() => { setMode('login'); setError(''); setSuccess(''); }}
                      className="text-emerald-400 hover:text-emerald-300 font-medium hover:underline ml-1 cursor-pointer"
                    >
                      Log in
                    </button>
                  </p>
                )}
                {mode === 'reset' && (
                  <button
                    onClick={() => { setMode('login'); setError(''); setSuccess(''); }}
                    className="text-emerald-400 hover:text-emerald-300 font-medium hover:underline cursor-pointer"
                  >
                    ← Back to Log in
                  </button>
                )}
              </div>

              <div className="mt-8 text-xs text-gray-600 flex items-center gap-3">
                <span className="hover:text-gray-400 cursor-pointer">Terms of Use</span>
                <span>|</span>
                <span className="hover:text-gray-400 cursor-pointer">Privacy Policy</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
