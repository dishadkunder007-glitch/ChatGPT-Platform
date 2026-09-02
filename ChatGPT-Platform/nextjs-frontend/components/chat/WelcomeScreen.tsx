'use client';

import { useStore } from '@/lib/store';
import { Zap, Code, FileText, Brain, Search, Sparkles } from 'lucide-react';

const SUGGESTIONS = [
  { icon: Brain, label: 'Explain machine learning', text: 'Explain machine learning in simple terms with examples' },
  { icon: Code, label: 'Write a Python function', text: 'Write a Python function to sort a list of dictionaries by a key' },
  { icon: Zap, label: 'Summarize a topic', text: 'Summarize the key concepts of the Transformer architecture in AI' },
  { icon: FileText, label: 'Help with writing', text: 'Help me write a professional email requesting a meeting' },
  { icon: Search, label: 'Explain a concept', text: 'What is RAG (Retrieval-Augmented Generation) and how does it work?' },
  { icon: Sparkles, label: 'Creative writing', text: 'Write a short story about an AI that helps scientists cure diseases' },
];

interface WelcomeScreenProps {
  onSendMessage: (msg: string) => void;
}

export function WelcomeScreen({ onSendMessage }: WelcomeScreenProps) {
  const { user } = useStore();
  const firstName = user?.name?.split(' ')[0] || 'there';

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8">
      <div className="w-full max-w-2xl text-center">
        {/* Logo / Greeting */}
        <div className="mb-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-500/20">
            <Sparkles size={28} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            Hello, {firstName}! 👋
          </h1>
          <p className="text-gray-400 text-lg">
            How can I help you today?
          </p>
        </div>

        {/* Suggestion grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-8">
          {SUGGESTIONS.map((s) => (
            <button
              key={s.label}
              onClick={() => onSendMessage(s.text)}
              className="flex items-start gap-3 p-4 rounded-xl bg-[#1a1a1a] hover:bg-[#252525] border border-[#2d2d2d] hover:border-[#444] transition-all text-left group"
            >
              <div className="w-8 h-8 rounded-lg bg-[#2d2d2d] group-hover:bg-emerald-500/20 flex items-center justify-center flex-shrink-0 transition-colors">
                <s.icon size={16} className="text-gray-400 group-hover:text-emerald-400 transition-colors" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">{s.label}</p>
                <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{s.text}</p>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
