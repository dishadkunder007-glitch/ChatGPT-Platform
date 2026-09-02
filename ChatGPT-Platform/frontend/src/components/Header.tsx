import React, { useState } from 'react';
import { Bot, Plus, Settings, User, LogOut, ChevronDown, Sparkles, Check, Zap, ShieldCheck } from 'lucide-react';
import { ModelOption, User as UserType } from '../types';

interface HeaderProps {
  currentModel: string;
  onSelectModel: (modelId: string) => void;
  models: ModelOption[];
  user: UserType | null;
  onNewChat: () => void;
  onOpenSettings: () => void;
  onOpenAuth: () => void;
  onLogout: () => void;
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentModel,
  onSelectModel,
  models,
  user,
  onNewChat,
  onOpenSettings,
  onOpenAuth,
  onLogout,
}) => {
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);

  const activeModelObj = models.find((m) => m.id === currentModel) || {
    id: currentModel,
    name: 'Llama 3.3 70B Versatile',
    badge: '🚀 Groq Cloud',
    provider: 'Groq Cloud',
  };

  return (
    <header className="h-16 border-b border-white/[0.08] bg-[#0b0f19]/80 backdrop-blur-xl flex items-center justify-between px-4 sm:px-6 sticky top-0 z-30 select-none shadow-sm">
      {/* Left Branding */}
      <div className="flex items-center space-x-3">
        <div className="relative group cursor-pointer" onClick={onNewChat}>
          <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-xl blur opacity-40 group-hover:opacity-80 transition duration-300"></div>
          <div className="relative w-9 h-9 rounded-xl bg-[#0f172a] border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-inner">
            <Bot className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </div>
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-extrabold text-base sm:text-lg bg-gradient-to-r from-white via-gray-200 to-emerald-300 bg-clip-text text-transparent tracking-tight">
              ChatGPT Platform
            </span>
            <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1"></span>
              v3.0 Ultra
            </span>
          </div>
        </div>
      </div>

      {/* Center Model Selector */}
      <div className="relative">
        <button
          onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
          className="flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs sm:text-sm text-gray-200 font-medium transition-all shadow-sm hover:border-emerald-500/40 group"
        >
          <Zap className="w-3.5 h-3.5 text-amber-400 group-hover:scale-110 transition-transform" />
          <span className="truncate max-w-[160px] sm:max-w-[240px] font-semibold">{activeModelObj.name}</span>
          <span className="hidden md:inline text-[10px] px-1.5 py-0.5 rounded bg-white/[0.08] text-emerald-400 font-mono">
            {activeModelObj.badge}
          </span>
          <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform duration-200 ${modelDropdownOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* Model dropdown menu */}
        {modelDropdownOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setModelDropdownOpen(false)} />
            <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 w-84 sm:w-96 bg-[#0f172a] border border-white/[0.12] rounded-2xl shadow-2xl z-50 p-2 animate-in fade-in zoom-in-95 backdrop-blur-2xl">
              <div className="px-3 py-2 text-[11px] font-bold text-gray-400 uppercase tracking-wider border-b border-white/[0.08] mb-1 flex items-center justify-between">
                <span>Select Hosted LLM Engine</span>
                <span className="text-emerald-400 font-mono text-[10px]">Cloud Hosted</span>
              </div>
              <div className="space-y-1.5 max-h-80 overflow-y-auto">
                {models.map((model) => {
                  const isSelected = model.id === currentModel;
                  return (
                    <button
                      key={model.id}
                      onClick={() => {
                        onSelectModel(model.id);
                        setModelDropdownOpen(false);
                      }}
                      className={`w-full text-left p-3 rounded-xl flex items-start justify-between transition-all ${
                        isSelected
                          ? 'bg-emerald-500/15 border border-emerald-500/40 text-white shadow-sm'
                          : 'hover:bg-white/[0.06] text-gray-300'
                      }`}
                    >
                      <div className="pr-2">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-xs sm:text-sm text-white">{model.name}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.08] text-emerald-400 font-mono font-semibold">
                            {model.badge}
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-400 mt-1 leading-snug">{model.description}</p>
                      </div>
                      {isSelected && <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-1" />}
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* + New Chat radiant button */}
        <button
          onClick={onNewChat}
          className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white text-xs sm:text-sm font-bold rounded-xl shadow-lg shadow-emerald-500/20 transition-all active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          title="Settings & API Keys"
          className="p-2 text-gray-400 hover:text-white hover:bg-white/[0.08] rounded-xl transition-all"
        >
          <Settings className="w-4 h-4" />
        </button>

        {/* User profile pill */}
        <button
          onClick={user?.is_guest ? onOpenAuth : onOpenSettings}
          className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs text-gray-300 border border-white/[0.08] transition-all"
        >
          <div className="w-5 h-5 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <User className="w-3.5 h-3.5" />
          </div>
          <span className="max-w-[90px] sm:max-w-[120px] truncate font-semibold">{user?.name || 'Guest User'}</span>
        </button>

        {/* Logout or Login button */}
        {user && !user.is_guest ? (
          <button
            onClick={onLogout}
            title="Log out"
            className="p-2 text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition-all"
          >
            <LogOut className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={onOpenAuth}
            title="Sign In / Register"
            className="p-2 text-emerald-400 hover:bg-emerald-500/10 rounded-xl transition-all"
          >
            <LogOut className="w-4 h-4 rotate-180" />
          </button>
        )}
      </div>
    </header>
  );
};
