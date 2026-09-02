import React, { useState, useEffect } from 'react';
import { X, Key, Cpu, Sliders, Check, Sparkles } from 'lucide-react';
import { User, ModelOption } from '../types';
import { updateUserProfile } from '../api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
  models: ModelOption[];
  currentModel: string;
  onSelectModel: (m: string) => void;
  temperature: number;
  setTemperature: (val: number) => void;
  systemPrompt: string;
  setSystemPrompt: (val: string) => void;
  onUserUpdated: (u: Partial<User>) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  user,
  models,
  currentModel,
  onSelectModel,
  temperature,
  setTemperature,
  systemPrompt,
  setSystemPrompt,
  onUserUpdated,
}) => {
  const [apiKey, setApiKey] = useState(user?.custom_api_key || '');
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (user) {
      setApiKey(user.custom_api_key || '');
    }
  }, [user]);

  if (!isOpen) return null;

  const handleSave = async () => {
    try {
      await updateUserProfile({
        custom_api_key: apiKey.trim(),
        preferred_model: currentModel,
        system_prompt: systemPrompt,
      });
      onUserUpdated({
        custom_api_key: apiKey.trim(),
        preferred_model: currentModel,
        system_prompt: systemPrompt,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
      <div className="bg-[#191e27] border border-[#2b3342] rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#282f3c] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <Sliders className="w-5 h-5 text-[#10a37f]" />
            <h3 className="font-bold text-base text-white">Platform Settings</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#8e8ea0] hover:text-white hover:bg-[#252c39] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 overflow-y-auto max-h-[70vh]">
          {/* Groq Cloud API Key */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-white flex items-center space-x-1.5">
                <Key className="w-3.5 h-3.5 text-amber-400" />
                <span>Custom Groq API Key (Optional)</span>
              </label>
              <a
                href="https://console.groq.com"
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-[#10a37f] hover:underline"
              >
                Get Free Key ↗
              </a>
            </div>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="gsk_..."
              className="w-full px-3.5 py-2 rounded-xl bg-[#141820] border border-[#283244] text-xs text-white placeholder-[#6e7681] focus:outline-none focus:border-[#10a37f]"
            />
            <p className="text-[11px] text-[#6e7681]">
              Leave empty to use the built-in hosted cloud inference service with zero setup.
            </p>
          </div>

          {/* Default Model */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-white flex items-center space-x-1.5">
              <Cpu className="w-3.5 h-3.5 text-[#10a37f]" />
              <span>Default AI Model</span>
            </label>
            <select
              value={currentModel}
              onChange={(e) => onSelectModel(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-[#141820] border border-[#283244] text-xs text-white focus:outline-none focus:border-[#10a37f]"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id} className="bg-[#141820]">
                  {m.name} ({m.provider})
                </option>
              ))}
            </select>
          </div>

          {/* Temperature Slider */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold text-white">
              <span>Temperature (Creativity): {temperature}</span>
              <span className="text-[11px] text-[#8e8ea0]">{temperature < 0.4 ? 'Precise / Deterministic' : 'Creative / Balanced'}</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-[#10a37f] bg-[#141820] cursor-pointer"
            />
          </div>

          {/* Custom System Prompt */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-white flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#10a37f]" />
              <span>Custom System Instructions</span>
            </label>
            <textarea
              rows={3}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="You are ChatGPT, a helpful and precise AI assistant..."
              className="w-full px-3.5 py-2 rounded-xl bg-[#141820] border border-[#283244] text-xs text-white placeholder-[#6e7681] focus:outline-none focus:border-[#10a37f] resize-none"
            />
          </div>

          {savedSuccess && (
            <div className="p-2.5 rounded-lg bg-[#10a37f]/15 border border-[#10a37f]/40 text-xs text-[#10a37f] flex items-center space-x-2">
              <Check className="w-4 h-4" />
              <span>Settings updated successfully!</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-[#282f3c] bg-[#141820] flex justify-end space-x-2.5">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 text-xs text-[#8e8ea0] hover:text-white rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-1.5 bg-[#10a37f] hover:bg-[#0e8e6e] text-white text-xs font-semibold rounded-lg shadow transition-all active:scale-95"
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
};
