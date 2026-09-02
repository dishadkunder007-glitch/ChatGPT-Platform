import React, { useEffect, useRef, useState } from 'react';
import { Bot, User, Copy, Check, ThumbsUp, ThumbsDown, RotateCcw, Edit3, FileCheck, Volume2, Sparkles, Code2, BrainCircuit, FileSearch, PenTool } from 'lucide-react';
import { Message, Citation } from '../types';

interface ChatAreaProps {
  messages: Message[];
  isStreaming: boolean;
  onRegenerate?: (messageId: string) => void;
  onEditMessage?: (messageId: string, newContent: string) => void;
  onFeedback?: (messageId: string, feedback: number) => void;
  onSelectPrompt?: (promptText: string) => void;
  userName?: string;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isStreaming,
  onRegenerate,
  onEditMessage,
  onFeedback,
  onSelectPrompt,
  userName,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [editingMsgId, setEditingMsgId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [speakingId, setSpeakingId] = useState<string | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleStartEdit = (msg: Message) => {
    setEditingMsgId(msg.id);
    setEditText(msg.content);
  };

  const handleSaveEdit = (msgId: string) => {
    if (editText.trim() && onEditMessage) {
      onEditMessage(msgId, editText.trim());
    }
    setEditingMsgId(null);
  };

  const handleSpeak = (id: string, text: string) => {
    if ('speechSynthesis' in window) {
      if (speakingId === id) {
        window.speechSynthesis.cancel();
        setSpeakingId(null);
      } else {
        window.speechSynthesis.cancel();
        const cleanText = text.replace(/[*_#`[\]()]/g, '');
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.05;
        utterance.onend = () => setSpeakingId(null);
        utterance.onerror = () => setSpeakingId(null);
        window.speechSynthesis.speak(utterance);
        setSpeakingId(id);
      }
    }
  };

  const getTimeGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center select-none overflow-y-auto max-w-4xl mx-auto w-full">
        {/* Animated Hero Header */}
        <div className="relative group mb-5">
          <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 rounded-3xl blur-md opacity-30 group-hover:opacity-60 transition duration-500"></div>
          <div className="relative w-20 h-20 rounded-3xl bg-[#0f172a] border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-2xl">
            <Bot className="w-10 h-10 animate-pulse" />
          </div>
        </div>

        <h1 className="text-2xl sm:text-3xl font-extrabold text-white mb-2 tracking-tight">
          {getTimeGreeting()}, <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">{userName || 'Explorer'}</span> ✨
        </h1>
        <p className="text-xs sm:text-sm text-gray-400 max-w-lg mb-8 leading-relaxed">
          Ask any question in depth, explore code, solve complex problems, or analyze documents with fast hosted cloud inference.
        </p>

        {/* Interactive Suggestion Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 w-full text-left">
          <div
            onClick={() => onSelectPrompt && onSelectPrompt('Hi, how are you!!')}
            className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] hover:border-emerald-500/50 cursor-pointer transition-all hover:scale-[1.01] group shadow-lg"
          >
            <div className="flex items-center space-x-2.5 text-emerald-400 mb-1.5">
              <Sparkles className="w-4 h-4" />
              <span className="text-xs font-bold text-white group-hover:text-emerald-300">Quick Greeting & Check-In</span>
            </div>
            <p className="text-[12px] text-gray-400">Say hi to the assistant and test conversational readiness.</p>
          </div>

          <div
            onClick={() => onSelectPrompt && onSelectPrompt('Explain Machine Learning in detail with core paradigms and a code example')}
            className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] hover:border-emerald-500/50 cursor-pointer transition-all hover:scale-[1.01] group shadow-lg"
          >
            <div className="flex items-center space-x-2.5 text-teal-400 mb-1.5">
              <BrainCircuit className="w-4 h-4" />
              <span className="text-xs font-bold text-white group-hover:text-teal-300">Machine Learning Deep Dive</span>
            </div>
            <p className="text-[12px] text-gray-400">Paradigms, lifecycle, evaluation metrics, and Python implementation.</p>
          </div>

          <div
            onClick={() => onSelectPrompt && onSelectPrompt('Explain the key differences between CNNs and Transformers with an architecture comparison table')}
            className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] hover:border-emerald-500/50 cursor-pointer transition-all hover:scale-[1.01] group shadow-lg"
          >
            <div className="flex items-center space-x-2.5 text-cyan-400 mb-1.5">
              <Code2 className="w-4 h-4" />
              <span className="text-xs font-bold text-white group-hover:text-cyan-300">CNN vs Transformers Comparison</span>
            </div>
            <p className="text-[12px] text-gray-400">Structural differences, attention mechanisms, and performance trade-offs.</p>
          </div>

          <div
            onClick={() => onSelectPrompt && onSelectPrompt('How does RAG (Retrieval Augmented Generation) work with vector search?')}
            className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] hover:border-emerald-500/50 cursor-pointer transition-all hover:scale-[1.01] group shadow-lg"
          >
            <div className="flex items-center space-x-2.5 text-amber-400 mb-1.5">
              <FileSearch className="w-4 h-4" />
              <span className="text-xs font-bold text-white group-hover:text-amber-300">RAG Document Analysis</span>
            </div>
            <p className="text-[12px] text-gray-400">Vector embeddings, chunking strategies, cosine similarity & citations.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-6 max-w-4xl mx-auto w-full">
      {messages.map((msg, index) => {
        const isUser = msg.role === 'user';
        const isLastAssistant = !isUser && index === messages.length - 1;
        const wordCount = msg.content ? msg.content.trim().split(/\s+/).length : 0;

        return (
          <div key={msg.id || index} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} group animate-in fade-in`}>
            <div className={`flex items-start space-x-3.5 max-w-[94%] sm:max-w-[88%] ${isUser ? 'flex-row-reverse space-x-reverse' : 'flex-row'}`}>
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-md ${
                  isUser
                    ? 'bg-[#1e293b] text-gray-200 border border-white/[0.12]'
                    : 'bg-gradient-to-tr from-emerald-500 to-teal-500 text-white shadow-emerald-500/20'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Content Bubble */}
              <div className="flex flex-col max-w-full">
                {isUser && editingMsgId === msg.id ? (
                  <div className="p-3.5 bg-[#1e2433] border border-emerald-500/80 rounded-2xl w-full shadow-xl">
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      className="w-full bg-transparent text-white text-sm focus:outline-none resize-none"
                      rows={3}
                      autoFocus
                    />
                    <div className="flex justify-end space-x-2 mt-2">
                      <button
                        onClick={() => setEditingMsgId(null)}
                        className="px-3 py-1 text-xs text-gray-400 hover:text-white rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSaveEdit(msg.id)}
                        className="px-3.5 py-1 text-xs bg-emerald-500 hover:bg-emerald-400 text-white font-bold rounded-lg shadow"
                      >
                        Save & Resubmit
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    className={`px-4 sm:px-5 py-3.5 rounded-2xl text-sm leading-relaxed ${
                      isUser
                        ? 'bg-gradient-to-r from-[#1e293b] to-[#172033] text-white rounded-tr-sm border border-white/[0.1] shadow-md'
                        : 'bg-[#0f172a]/90 text-gray-200 rounded-tl-sm border border-white/[0.08] shadow-lg backdrop-blur-md'
                    }`}
                  >
                    <div className="markdown-body whitespace-pre-wrap select-text">
                      {msg.content}
                      {msg.isStreaming && <span className="streaming-cursor" />}
                    </div>

                    {/* Citations block if grounded in documents */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 pt-3.5 border-t border-white/[0.08] space-y-2.5">
                        <div className="text-[11px] font-bold text-emerald-400 flex items-center space-x-2 uppercase tracking-wider">
                          <FileCheck className="w-4 h-4 text-emerald-400" />
                          <span>Grounded Document Sources ({msg.citations.length})</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-1.5">
                          {msg.citations.map((cit, cIdx) => (
                            <div
                              key={cIdx}
                              className="p-3 rounded-xl bg-black/30 border border-white/[0.08] text-[11px] hover:border-emerald-500/40 transition-colors"
                            >
                              <div className="font-bold text-white truncate flex items-center justify-between">
                                <span className="truncate">{cit.filename}</span>
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono ml-1">
                                  p. {cit.page}
                                </span>
                              </div>
                              <p className="text-gray-400 line-clamp-2 mt-1 leading-snug">{cit.text}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Message action controls below bubble */}
                <div
                  className={`flex items-center space-x-2.5 mt-2 text-gray-500 px-1 text-xs ${
                    isUser ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {/* Word count badge */}
                  {!isUser && !msg.isStreaming && wordCount > 0 && (
                    <span className="text-[10px] text-gray-500 font-mono">
                      {wordCount} words
                    </span>
                  )}

                  {/* Copy Button */}
                  <button
                    onClick={() => handleCopy(msg.id || String(index), msg.content)}
                    title="Copy text"
                    className="p-1 hover:text-white transition-colors rounded-lg hover:bg-white/[0.06]"
                  >
                    {copiedId === (msg.id || String(index)) ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>

                  {/* Text-to-speech button */}
                  {!isUser && !msg.isStreaming && (
                    <button
                      onClick={() => handleSpeak(msg.id || String(index), msg.content)}
                      title={speakingId === (msg.id || String(index)) ? 'Stop speaking' : 'Read aloud'}
                      className={`p-1 transition-colors rounded-lg hover:bg-white/[0.06] ${
                        speakingId === (msg.id || String(index)) ? 'text-emerald-400 animate-pulse' : 'hover:text-white'
                      }`}
                    >
                      <Volume2 className="w-3.5 h-3.5" />
                    </button>
                  )}

                  {/* User Edit button */}
                  {isUser && onEditMessage && (
                    <button
                      onClick={() => handleStartEdit(msg)}
                      title="Edit message"
                      className="p-1 hover:text-white transition-colors rounded-lg hover:bg-white/[0.06]"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                  )}

                  {/* Assistant Thumbs Feedback & Regenerate */}
                  {!isUser && !msg.isStreaming && (
                    <>
                      <button
                        onClick={() => onFeedback && onFeedback(msg.id, msg.feedback === 1 ? 0 : 1)}
                        title="Good response"
                        className={`p-1 transition-colors rounded-lg hover:bg-white/[0.06] ${
                          msg.feedback === 1 ? 'text-emerald-400' : 'hover:text-white'
                        }`}
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onFeedback && onFeedback(msg.id, msg.feedback === -1 ? 0 : -1)}
                        title="Bad response"
                        className={`p-1 transition-colors rounded-lg hover:bg-white/[0.06] ${
                          msg.feedback === -1 ? 'text-rose-400' : 'hover:text-white'
                        }`}
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                      </button>

                      {isLastAssistant && onRegenerate && (
                        <button
                          onClick={() => onRegenerate(msg.id)}
                          title="Regenerate response"
                          className="p-1 hover:text-white transition-colors rounded-lg hover:bg-white/[0.06] flex items-center space-x-1"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
};
