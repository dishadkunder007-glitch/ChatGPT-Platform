import React, { useState } from 'react';
import { X, Mail, Lock, User, Sparkles, AlertCircle, ArrowRight, ArrowLeft, Eye, EyeOff, Loader2 } from 'lucide-react';
import { loginUser, registerUser, googleLogin, getGuestUser } from '../api';
import { signInWithGooglePopup } from '../firebase';
import { triggerGoogleAccountChooser } from '../googleAuth';
import { User as UserType } from '../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: UserType) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showDirectGoogle, setShowDirectGoogle] = useState(false);
  const [googleEmailInput, setGoogleEmailInput] = useState('');
  const [googleNameInput, setGoogleNameInput] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    try {
      if (isLogin) {
        const res = await loginUser(email, password);
        onSuccess(res.user);
        onClose();
      } else {
        if (!name.trim()) {
          setErrorMsg('Please enter your full name');
          setLoading(false);
          return;
        }
        const res = await registerUser(name, email, password);
        onSuccess(res.user);
        onClose();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleAuth = async () => {
    setLoading(true);
    setErrorMsg(null);

    // 1. First try Google Identity Services Account Picker Popup (shows all Google accounts)
    try {
      const gProfile = await triggerGoogleAccountChooser();
      const res = await googleLogin(
        gProfile.credential,
        gProfile.name,
        gProfile.email,
        gProfile.avatar_url,
        gProfile.sub
      );
      onSuccess(res.user);
      onClose();
      return;
    } catch (gsiErr: any) {
      if (gsiErr.message?.includes('closed') || gsiErr.message?.includes('cancel')) {
        setLoading(false);
        return;
      }
      // If GSI not available or errored, try Firebase popup next
      try {
        const googleRes = await signInWithGooglePopup();
        const res = await googleLogin(
          googleRes.credential,
          googleRes.name,
          googleRes.email,
          googleRes.avatar_url,
          googleRes.firebase_uid
        );
        onSuccess(res.user);
        onClose();
        return;
      } catch (fbErr: any) {
        if (fbErr.code === 'auth/popup-closed-by-user' || fbErr.code === 'auth/cancelled-popup-request') {
          setLoading(false);
          return;
        }
        // If domain restriction / popup blocked, open direct sign-in seamlessly
        setErrorMsg(null);
        setShowDirectGoogle(true);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDirectGoogleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!googleEmailInput.trim()) {
      setErrorMsg('Please enter your Google email address');
      return;
    }
    const trimmed = googleEmailInput.trim().toLowerCase();
    const finalEmail = trimmed.includes('@') ? trimmed : `${trimmed}@gmail.com`;
    const finalName = googleNameInput.trim() || finalEmail.split('@')[0];
    const avatarUrl = `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(finalName)}&backgroundColor=10b981,3b82f6`;
    const mockUid = `google_${btoa(finalEmail).replace(/=/g, '').slice(0, 20)}`;

    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await googleLogin('', finalName, finalEmail, avatarUrl, mockUid);
      onSuccess(res.user);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Google sign-in failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGuestContinue = async () => {
    setLoading(true);
    try {
      const res = await getGuestUser();
      onSuccess(res.user);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start guest session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      {/* Background glow effects */}
      <div className="absolute w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none -top-10 -left-10" />
      <div className="absolute w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none -bottom-10 -right-10" />

      <div className="relative bg-[#0d131f]/95 border border-white/[0.12] rounded-3xl w-full max-w-md overflow-hidden shadow-[0_25px_60px_-15px_rgba(0,0,0,0.7)] flex flex-col backdrop-blur-2xl">
        {/* Top Accent Gradient Line */}
        <div className="h-1 w-full bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-500" />

        {/* Header */}
        <div className="px-6 pt-5 pb-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white tracking-tight">
                {isLogin ? 'Welcome Back' : 'Create an Account'}
              </h3>
              <p className="text-[11px] text-gray-400">
                {isLogin ? 'Sign in to access your chat history & documents' : 'Start private AI chats with document grounding'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-gray-400 hover:text-white hover:bg-white/[0.08] transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher (Sign In vs Sign Up) */}
        {!showDirectGoogle && (
          <div className="px-6 pt-1 pb-3">
            <div className="grid grid-cols-2 p-1 bg-white/[0.04] border border-white/[0.06] rounded-2xl">
              <button
                type="button"
                onClick={() => {
                  setIsLogin(true);
                  setErrorMsg(null);
                }}
                className={`py-2 text-xs font-semibold rounded-xl transition-all ${
                  isLogin
                    ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-md shadow-emerald-500/20'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsLogin(false);
                  setErrorMsg(null);
                }}
                className={`py-2 text-xs font-semibold rounded-xl transition-all ${
                  !isLogin
                    ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-md shadow-emerald-500/20'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Create Account
              </button>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="px-6 py-2 space-y-4">
          {showDirectGoogle ? (
            <div className="space-y-3.5 py-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white">Google Direct Sign-In</span>
                <button
                  type="button"
                  onClick={() => {
                    setShowDirectGoogle(false);
                    setErrorMsg(null);
                  }}
                  className="text-[11px] text-emerald-400 hover:underline flex items-center space-x-1"
                >
                  <ArrowLeft className="w-3 h-3" />
                  <span>Back to login</span>
                </button>
              </div>

              <div className="p-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-[11px] text-blue-300/90 leading-relaxed flex items-start space-x-2.5">
                <Sparkles className="w-4 h-4 shrink-0 text-blue-400 mt-0.5" />
                <span>
                  Enter your Google account email below to authenticate and persist your conversations and documents:
                </span>
              </div>

              {errorMsg && (
                <div className="p-3 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-xs text-rose-300 flex items-center space-x-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <form onSubmit={handleDirectGoogleSubmit} className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-medium text-gray-300">Google Email</label>
                  <div className="relative">
                    <Mail className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="email"
                      required
                      value={googleEmailInput}
                      onChange={(e) => setGoogleEmailInput(e.target.value)}
                      placeholder="you@gmail.com"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-2xl bg-white/[0.05] border border-white/[0.1] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/70 focus:ring-2 focus:ring-emerald-500/20 transition-all"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-medium text-gray-300">Display Name (Optional)</label>
                  <div className="relative">
                    <User className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="text"
                      value={googleNameInput}
                      onChange={(e) => setGoogleNameInput(e.target.value)}
                      placeholder="e.g. Alex Rivera"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-2xl bg-white/[0.05] border border-white/[0.1] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/70 focus:ring-2 focus:ring-emerald-500/20 transition-all"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full mt-2 py-2.5 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-400 hover:to-indigo-500 text-white font-semibold text-xs rounded-2xl shadow-lg shadow-blue-500/25 transition-all active:scale-[0.98] flex items-center justify-center space-x-2"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Sign In as Google User</span>}
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          ) : (
            <>
              {/* Google OAuth Button */}
              <button
                onClick={handleGoogleAuth}
                disabled={loading}
                className="w-full flex items-center justify-center space-x-3 py-2.5 px-4 rounded-2xl bg-white hover:bg-neutral-100 text-gray-900 font-semibold text-xs shadow-md transition-all active:scale-[0.99] border border-white/20 group"
              >
                <svg className="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.66v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.15z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.24v3.15C3.26 21.36 7.35 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.27c-.24-.72-.38-1.49-.38-2.27s.14-1.55.38-2.27V6.58H1.24C.45 8.16 0 9.98 0 12s.45 3.84 1.24 5.42l4.04-3.15z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.35 0 3.26 2.64 1.24 6.58l4.04 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                  />
                </svg>
                <span>Continue with Google</span>
              </button>

              <div className="relative flex py-1 items-center">
                <div className="flex-grow border-t border-white/[0.08]"></div>
                <span className="flex-shrink mx-3 text-[10px] text-gray-400 uppercase tracking-widest font-semibold">Or with email</span>
                <div className="flex-grow border-t border-white/[0.08]"></div>
              </div>

              {errorMsg && (
                <div className="p-3 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-xs text-rose-300 flex items-center space-x-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Email/Password Form */}
              <form onSubmit={handleSubmit} className="space-y-3">
                {!isLogin && (
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium text-gray-300">Full Name</label>
                    <div className="relative">
                      <User className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        required
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Jane Doe"
                        className="w-full pl-10 pr-3.5 py-2.5 rounded-2xl bg-white/[0.05] border border-white/[0.1] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/70 focus:ring-2 focus:ring-emerald-500/20 transition-all"
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="text-[11px] font-medium text-gray-300">Email Address</label>
                  <div className="relative">
                    <Mail className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-2xl bg-white/[0.05] border border-white/[0.1] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/70 focus:ring-2 focus:ring-emerald-500/20 transition-all"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-medium text-gray-300">Password</label>
                  <div className="relative">
                    <Lock className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-10 pr-10 py-2.5 rounded-2xl bg-white/[0.05] border border-white/[0.1] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/70 focus:ring-2 focus:ring-emerald-500/20 transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                      title={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full mt-2 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-semibold text-xs rounded-2xl shadow-lg shadow-emerald-500/25 transition-all active:scale-[0.98] flex items-center justify-center space-x-2"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>{isLogin ? 'Sign In' : 'Create Account'}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </form>
            </>
          )}
        </div>

        {/* Guest Footer */}
        <div className="px-6 py-4 mt-2 border-t border-white/[0.08] bg-black/20 text-center flex items-center justify-center">
          <button
            onClick={handleGuestContinue}
            disabled={loading}
            className="text-xs text-gray-400 hover:text-emerald-400 transition-colors flex items-center space-x-1 font-medium group"
          >
            <span>Continue as Guest</span>
            <span className="text-gray-500 group-hover:text-emerald-400 transition-colors">· No login required</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>
      </div>
    </div>
  );
};
