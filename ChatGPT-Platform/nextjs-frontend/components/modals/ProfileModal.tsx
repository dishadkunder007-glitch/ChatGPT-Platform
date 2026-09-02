'use client';

import { useState } from 'react';
import { X, Camera, Loader2, AlertTriangle, Key, User, Mail } from 'lucide-react';
import { useStore } from '@/lib/store';
import * as api from '@/lib/api';
import { signOutFirebase } from '@/lib/firebase';
import { cn } from '@/lib/utils';

interface ProfileModalProps {
  onClose: () => void;
}

export function ProfileModal({ onClose }: ProfileModalProps) {
  const { user, setUser, logout } = useStore();
  const [tab, setTab] = useState<'profile' | 'password' | 'danger'>('profile');
  const [name, setName] = useState(user?.name || '');
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState('');

  async function saveProfile() {
    if (!name.trim()) { setError('Name cannot be empty'); return; }
    setSaving(true); setError(''); setSuccess('');
    try {
      const result = await api.updateProfile({ name: name.trim() });
      setUser({ ...user!, name: name.trim() });
      setSuccess('Profile updated successfully!');
    } catch (e: any) { setError(e.message); }
    setSaving(false);
  }

  async function changePassword() {
    if (newPw !== confirmPw) { setError('Passwords do not match'); return; }
    if (newPw.length < 8) { setError('Password must be at least 8 characters'); return; }
    setSaving(true); setError(''); setSuccess('');
    try {
      await api.changePassword(currentPw, newPw);
      setSuccess('Password changed successfully!');
      setCurrentPw(''); setNewPw(''); setConfirmPw('');
    } catch (e: any) { setError(e.message); }
    setSaving(false);
  }

  async function deleteAccount() {
    if (deleteConfirm !== 'DELETE') { setError('Type DELETE to confirm'); return; }
    setSaving(true);
    try {
      await api.deleteAccount();
      try {
        await signOutFirebase();
      } catch { }
      logout();
      api.removeToken();
      localStorage.removeItem('auth_token');
      onClose();
      window.location.reload();
    } catch (e: any) { setError(e.message); }
    setSaving(false);
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#1a1a1a] border border-[#333] rounded-2xl w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#2d2d2d]">
          <h2 className="text-lg font-semibold text-white">Profile & Account</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[#2d2d2d] text-gray-400 hover:text-white">
            <X size={18} />
          </button>
        </div>

        {/* Avatar section */}
        <div className="px-6 pt-5 flex items-center gap-4">
          <div className="relative">
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="" className="w-16 h-16 rounded-full object-cover" />
            ) : (
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center text-2xl font-bold text-white">
                {user?.name.charAt(0).toUpperCase()}
              </div>
            )}
          </div>
          <div>
            <p className="text-white font-semibold">{user?.name}</p>
            <p className="text-sm text-gray-500">{user?.email}</p>
            <p className="text-xs text-gray-600 mt-0.5">
              Member since {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'recently'}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[#2d2d2d] px-4 mt-4">
          {(['profile', 'password', 'danger'] as const).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(''); setSuccess(''); }}
              className={cn(
                'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                tab === t
                  ? t === 'danger' ? 'border-red-500 text-red-400' : 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-gray-500 hover:text-white'
              )}
            >
              {t === 'profile' ? 'Profile' : t === 'password' ? 'Password' : 'Danger Zone'}
            </button>
          ))}
        </div>

        <div className="p-6 space-y-4">
          {/* Messages */}
          {error && <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400">{error}</div>}
          {success && <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-4 py-3 text-sm text-emerald-400">{success}</div>}

          {tab === 'profile' && (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Full Name</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-[#212121] border border-[#333] rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-emerald-500/50 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Email</label>
                <input
                  value={user?.email || ''}
                  disabled
                  className="w-full bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl px-4 py-3 text-sm text-gray-500 cursor-not-allowed"
                />
              </div>
              <button
                onClick={saveProfile}
                disabled={saving}
                className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Profile'}
              </button>
            </>
          )}

          {tab === 'password' && (
            <>
              {['Current Password', 'New Password', 'Confirm Password'].map((label, i) => (
                <div key={label}>
                  <label className="block text-xs font-medium text-gray-400 mb-1">{label}</label>
                  <input
                    type="password"
                    value={[currentPw, newPw, confirmPw][i]}
                    onChange={(e) => [setCurrentPw, setNewPw, setConfirmPw][i](e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-[#212121] border border-[#333] rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-emerald-500/50 transition-colors"
                  />
                </div>
              ))}
              <button
                onClick={changePassword}
                disabled={saving || !currentPw || !newPw || !confirmPw}
                className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
              >
                {saving ? 'Changing...' : 'Change Password'}
              </button>
            </>
          )}

          {tab === 'danger' && (
            <div className="space-y-4">
              <div className="bg-red-500/5 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={16} className="text-red-400" />
                  <p className="text-sm font-medium text-red-400">Delete Account</p>
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">
                  This will permanently delete your account, all conversations, and all uploaded documents. This cannot be undone.
                </p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Type "DELETE" to confirm</label>
                <input
                  value={deleteConfirm}
                  onChange={(e) => setDeleteConfirm(e.target.value)}
                  placeholder="DELETE"
                  className="w-full bg-[#212121] border border-red-500/30 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-red-500 transition-colors font-mono"
                />
              </div>
              <button
                onClick={deleteAccount}
                disabled={saving || deleteConfirm !== 'DELETE'}
                className="w-full py-2.5 rounded-xl bg-red-600/80 hover:bg-red-600 text-white text-sm font-medium transition-colors disabled:opacity-30"
              >
                {saving ? 'Deleting...' : 'Delete My Account'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
