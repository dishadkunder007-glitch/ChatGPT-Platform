'use client';

import { useState } from 'react';
import { X, Save, Key, Sliders, Bot, ChevronDown } from 'lucide-react';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import * as api from '@/lib/api';

interface SettingsModalProps {
  onClose: () => void;
}

export function SettingsModal({ onClose }: SettingsModalProps) {
  const {
    models, currentModel, setCurrentModel,
    temperature, setTemperature,
    systemPrompt, setSystemPrompt,
    useRag, setUseRag,
    user, setUser,
  } = useStore();

  const [localPrompt, setLocalPrompt] = useState(systemPrompt);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<'model' | 'advanced'>('model');

  async function handleSave() {
    setSaving(true);
    try {
      setSystemPrompt(localPrompt);
      if (user && !user.is_guest) {
        await api.updateProfile({
          preferred_model: currentModel,
          system_prompt: localPrompt,
        });
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { }
    setSaving(false);
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#1a1a1a] border border-[#333] rounded-2xl w-full max-w-lg shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#2d2d2d]">
          <h2 className="text-lg font-semibold text-white">Settings</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[#2d2d2d] text-gray-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[#2d2d2d] px-4">
          {(['model', 'advanced'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'px-4 py-3 text-sm font-medium border-b-2 transition-colors capitalize',
                activeTab === tab
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-gray-500 hover:text-white'
              )}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        <div className="p-6 space-y-5 max-h-[60vh] overflow-y-auto">
          {activeTab === 'model' && (
            <>
              <div>
                <label className="block text-sm font-medium text-white mb-2">AI Model</label>
                <div className="space-y-2">
                  {models.map((model) => (
                    <button
                      key={model.id}
                      onClick={() => setCurrentModel(model.id)}
                      className={cn(
                        'w-full flex items-start gap-3 p-3 rounded-xl text-left border transition-all',
                        currentModel === model.id
                          ? 'border-emerald-500/50 bg-emerald-500/5'
                          : 'border-[#2d2d2d] hover:border-[#444] bg-[#212121]'
                      )}
                    >
                      <div className={cn(
                        'w-4 h-4 rounded-full border-2 flex-shrink-0 mt-0.5 transition-all',
                        currentModel === model.id ? 'border-emerald-500 bg-emerald-500' : 'border-[#555]'
                      )} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-white">{model.name}</span>
                          <span className="text-xs px-1.5 py-0.5 bg-[#333] text-gray-400 rounded">{model.badge}</span>
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">{model.description}</p>
                        <p className="text-xs text-gray-600 mt-0.5">{model.provider}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {activeTab === 'advanced' && (
            <>
              {/* Temperature */}
              <div>
                <label className="block text-sm font-medium text-white mb-1">
                  Temperature: <span className="text-emerald-400 font-mono">{temperature.toFixed(1)}</span>
                </label>
                <p className="text-xs text-gray-500 mb-3">Lower = more focused, Higher = more creative</p>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-emerald-500"
                />
                <div className="flex justify-between text-xs text-gray-600 mt-1">
                  <span>Precise (0.0)</span>
                  <span>Creative (1.0)</span>
                </div>
              </div>

              {/* System Prompt */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">System Prompt</label>
                <textarea
                  value={localPrompt}
                  onChange={(e) => setLocalPrompt(e.target.value)}
                  rows={5}
                  className="w-full bg-[#212121] border border-[#333] rounded-xl px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-emerald-500/50 transition-colors resize-none"
                  placeholder="You are a helpful AI assistant..."
                />
                <p className="text-xs text-gray-600 mt-1">
                  Custom instructions for how the AI should behave
                </p>
              </div>

              {/* RAG toggle */}
              <div className="flex items-center justify-between p-4 bg-[#212121] rounded-xl border border-[#2d2d2d]">
                <div>
                  <p className="text-sm font-medium text-white">Document Search (RAG)</p>
                  <p className="text-xs text-gray-500 mt-0.5">Use uploaded documents to answer questions</p>
                </div>
                <button
                  onClick={() => setUseRag(!useRag)}
                  className={cn(
                    'w-11 h-6 rounded-full transition-all duration-300 relative flex-shrink-0',
                    useRag ? 'bg-emerald-500' : 'bg-[#3d3d3d]'
                  )}
                >
                  <span className={cn(
                    'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-all duration-300',
                    useRag && 'translate-x-5'
                  )} />
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-6 pt-0 border-t border-[#2d2d2d] mt-4">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-xl border border-[#333] text-gray-300 hover:text-white hover:border-[#555] text-sm transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
          >
            {saved ? '✓ Saved!' : saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
