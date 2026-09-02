'use client';

import { useState } from 'react';
import { Menu, ChevronDown, Settings, LogIn, UserPlus, User as UserIcon } from 'lucide-react';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';

interface HeaderProps {
  onSettingsOpen: () => void;
  onAuthOpen: () => void;
  onProfileOpen: () => void;
}

export function Header({ onSettingsOpen, onAuthOpen, onProfileOpen }: HeaderProps) {
  const { isSidebarOpen, setSidebarOpen, conversations, activeConvId, models, currentModel, setCurrentModel, user } = useStore();
  const [modelDropdown, setModelDropdown] = useState(false);

  const activeConv = conversations.find((c) => c.id === activeConvId);
  const currentModelData = models.find((m) => m.id === currentModel);
  const isLoggedIn = user && !user.is_guest;

  return (
    <header className="flex items-center justify-between px-4 py-3 border-b border-[#2d2d2d] bg-[#0f0f0f] z-20 relative">
      {/* Left: hamburger + brand + Model Picker + Top-Left Auth */}
      <div className="flex items-center gap-3">
        {/* Sidebar toggle */}
        <button
          onClick={() => setSidebarOpen(!isSidebarOpen)}
          className="p-2 rounded-lg hover:bg-[#2d2d2d] text-gray-400 hover:text-white transition-colors"
          title={isSidebarOpen ? 'Close sidebar' : 'Open sidebar'}
        >
          <Menu size={18} />
        </button>

        {/* Model picker */}
        <div className="relative">
          <button
            onClick={() => setModelDropdown(!modelDropdown)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-[#2d2d2d] text-white text-sm font-medium transition-colors"
          >
            <span className="hidden sm:inline">{currentModelData?.name?.split(' ').slice(0, 3).join(' ') || 'ChatGPT Platform'}</span>
            <span className="sm:hidden">AI Model</span>
            <ChevronDown size={14} className={cn('transition-transform', modelDropdown && 'rotate-180')} />
          </button>

          {modelDropdown && (
            <div className="absolute top-full left-0 mt-2 w-80 bg-[#1a1a1a] border border-[#333] rounded-xl shadow-2xl z-50 overflow-hidden">
              <div className="p-2">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => { setCurrentModel(model.id); setModelDropdown(false); }}
                    className={cn(
                      'w-full flex items-start gap-3 p-3 rounded-lg text-left transition-colors',
                      currentModel === model.id ? 'bg-emerald-500/10 border border-emerald-500/30' : 'hover:bg-[#2d2d2d]'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">{model.name}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded-md bg-[#333] text-gray-400">{model.badge}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">{model.description}</p>
                    </div>
                    {currentModel === model.id && (
                      <div className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0 mt-1.5" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right: actions & profile */}
      <div className="flex items-center gap-2">
        {!isLoggedIn ? (
          <button
            onClick={() => onAuthOpen()}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:scale-[0.98] text-white text-xs font-semibold transition-all shadow-sm border border-emerald-500/40"
          >
            <LogIn size={13} />
            Log In
          </button>
        ) : (
          <button
            onClick={onProfileOpen}
            className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-[#2d2d2d] transition-colors"
            title="Profile"
          >
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full object-cover" />
            ) : (
              <div className="w-6 h-6 rounded-full bg-emerald-600 flex items-center justify-center text-xs font-bold text-white">
                {user.name?.charAt(0).toUpperCase()}
              </div>
            )}
            <span className="hidden md:inline text-xs font-medium text-gray-200">{user.name}</span>
          </button>
        )}

        <button
          onClick={onSettingsOpen}
          className="p-2 rounded-lg hover:bg-[#2d2d2d] text-gray-400 hover:text-white transition-colors"
          title="Settings"
        >
          <Settings size={16} />
        </button>
      </div>

      {/* Close dropdown on outside click */}
      {modelDropdown && (
        <div className="fixed inset-0 z-40" onClick={() => setModelDropdown(false)} />
      )}
    </header>
  );
}
