'use client';

import { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import * as api from '@/lib/api';

export function Providers({ children }: { children: React.ReactNode }) {
  const { token, setUser, setToken, logout, setModels } = useStore();
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    async function init() {
      const savedToken = localStorage.getItem('auth_token') || token;
      try {
        if (savedToken) {
          setToken(savedToken);
          api.setToken(savedToken);
          const user = await api.getCurrentUser();
          setUser(user);
        } else {
          // Auto-login as guest
          const res = await api.getGuestUser();
          setToken(res.access_token);
          api.setToken(res.access_token);
          localStorage.setItem('auth_token', res.access_token);
          setUser(res.user);
        }

        const rawModels = await api.getModels();
        const filteredModels = rawModels.filter(
          (m) =>
            !m.id.toLowerCase().includes('llama') &&
            !m.id.toLowerCase().includes('groq') &&
            !m.name.toLowerCase().includes('llama')
        );
        const hasQwen = filteredModels.some((m) => m.id === 'qwen2.5:1.5b');
        const updatedModels = hasQwen
          ? filteredModels
          : [
              {
                id: 'qwen2.5:1.5b',
                name: 'Qwen 2.5 1.5B',
                badge: 'Ollama',
                provider: 'Ollama',
                description: 'Local Ollama engine running Qwen 2.5 1.5B.',
                context_length: 32768,
                is_default: true,
              },
              ...filteredModels,
            ];
        setModels(updatedModels);
      } catch {
        logout();
      } finally {
        setInitialized(true);
      }
    }
    init();
  }, []);

  if (!initialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0f0f0f]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-emerald-500 border-t-transparent animate-spin" />
          <p className="text-gray-400 text-sm">Loading ChatGPT Platform...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
