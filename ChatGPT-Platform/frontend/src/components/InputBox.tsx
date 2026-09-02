import React, { useRef, useEffect } from 'react';
import { Paperclip, Square, ArrowUp, Sparkles, FileText } from 'lucide-react';

interface InputBoxProps {
  input: string;
  setInput: (val: string) => void;
  onSend: () => void;
  onStop: () => void;
  isStreaming: boolean;
  onOpenDocumentManager: () => void;
  attachedDocsCount: number;
  useRag: boolean;
}

export const InputBox: React.FC<InputBoxProps> = ({
  input,
  setInput,
  onSend,
  onStop,
  isStreaming,
  onOpenDocumentManager,
  attachedDocsCount,
  useRag,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isStreaming) {
        onSend();
      }
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-4 select-none">
      {/* Floating curved container with glassmorphic glow */}
      <div className="relative rounded-3xl bg-[#0f172a]/90 backdrop-blur-2xl border border-white/[0.12] shadow-2xl focus-within:border-emerald-500/80 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all flex items-end p-2 sm:p-2.5">
        {/* Paperclip attachment button */}
        <button
          onClick={onOpenDocumentManager}
          title="Upload or manage documents for RAG grounding"
          className="relative p-2.5 text-gray-400 hover:text-white hover:bg-white/[0.08] rounded-2xl transition-all shrink-0 group"
        >
          <Paperclip className="w-5 h-5 -rotate-45 group-hover:scale-110 transition-transform text-gray-400 group-hover:text-emerald-400" />
          {attachedDocsCount > 0 && (
            <span className="absolute top-1 right-1 px-1.5 py-0.2 rounded-full text-[9px] font-bold bg-emerald-500 text-black">
              {attachedDocsCount}
            </span>
          )}
        </button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything (e.g. 'Hi, how are you!!', explain concepts, write code, analyze docs)..."
          rows={1}
          className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-500 px-3 py-2.5 focus:outline-none resize-none max-h-48 overflow-y-auto leading-relaxed"
        />

        {/* Action Button: Red Stop or Fast Send */}
        <div className="shrink-0 pl-1.5 pb-0.5">
          {isStreaming ? (
            <button
              onClick={onStop}
              title="Stop generating"
              className="w-9 h-9 rounded-2xl bg-gradient-to-r from-rose-500 to-red-600 hover:from-rose-400 hover:to-red-500 text-white flex items-center justify-center transition-all shadow-lg shadow-rose-500/30 active:scale-95 animate-pulse"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
            </button>
          ) : (
            <button
              onClick={onSend}
              disabled={!input.trim()}
              title="Send message"
              className={`w-9 h-9 rounded-2xl flex items-center justify-center transition-all shadow-lg ${
                input.trim()
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white shadow-emerald-500/25 active:scale-95'
                  : 'bg-white/[0.05] text-gray-500 cursor-not-allowed border border-white/[0.05]'
              }`}
            >
              <ArrowUp className="w-4 h-4 stroke-[3]" />
            </button>
          )}
        </div>
      </div>

      {/* Footer information */}
      <div className="flex items-center justify-center space-x-2 mt-2 text-[11px] text-gray-500 text-center">
        <span>ChatGPT Platform v3.0</span>
        <span>•</span>
        <span className="flex items-center text-emerald-400/80">
          <Sparkles className="w-3 h-3 mr-1" />
          Hosted Cloud AI
        </span>
        <span>•</span>
        <span>Verify critical facts and inspect document citations</span>
      </div>
    </div>
  );
};
