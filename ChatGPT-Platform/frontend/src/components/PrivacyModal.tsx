import React, { useState } from 'react';
import {
  X,
  ShieldCheck,
  Lock,
  EyeOff,
  Database,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Server,
  FileText,
  Loader2,
} from 'lucide-react';
import { deleteAllDocuments, deleteConversation } from '../api';
import { Conversation } from '../types';

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: Conversation[];
  onConversationsPurged: () => void;
  onDocumentsPurged: () => void;
  isIncognito: boolean;
  onToggleIncognito: (val: boolean) => void;
}

export const PrivacyModal: React.FC<PrivacyModalProps> = ({
  isOpen,
  onClose,
  conversations,
  onConversationsPurged,
  onDocumentsPurged,
  isIncognito,
  onToggleIncognito,
}) => {
  const [purgingChats, setPurgingChats] = useState(false);
  const [purgingDocs, setPurgingDocs] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  if (!isOpen) return null;

  const handlePurgeAllChats = async () => {
    if (!window.confirm('Are you sure you want to permanently delete ALL your chat conversations? This cannot be undone.')) {
      return;
    }
    setPurgingChats(true);
    setStatusMsg(null);
    try {
      for (const conv of conversations) {
        await deleteConversation(conv.id);
      }
      onConversationsPurged();
      setStatusMsg({ type: 'success', text: 'All conversation history has been permanently wiped.' });
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: 'Failed to purge all conversations. Please try again.' });
    } finally {
      setPurgingChats(false);
    }
  };

  const handlePurgeAllDocs = async () => {
    if (!window.confirm('Are you sure you want to permanently wipe ALL your uploaded documents and vector embeddings?')) {
      return;
    }
    setPurgingDocs(true);
    setStatusMsg(null);
    try {
      await deleteAllDocuments();
      onDocumentsPurged();
      setStatusMsg({ type: 'success', text: 'All documents and vector memory have been completely purged.' });
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: 'Failed to purge documents.' });
    } finally {
      setPurgingDocs(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      {/* Background glow accents */}
      <div className="absolute w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none -top-10 -left-10" />
      <div className="absolute w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none -bottom-10 -right-10" />

      <div className="relative bg-[#0d131f]/95 border border-white/[0.12] rounded-3xl w-full max-w-xl overflow-hidden shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8)] flex flex-col backdrop-blur-2xl max-h-[90vh]">
        {/* Top Accent Gradient */}
        <div className="h-1 w-full bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-500" />

        {/* Modal Header */}
        <div className="px-6 pt-5 pb-4 flex items-center justify-between border-b border-white/[0.08]">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white tracking-tight flex items-center space-x-2">
                <span>Chat Privacy & Data Security</span>
                <span className="px-2 py-0.5 text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold rounded-full border border-emerald-500/30">
                  Protected
                </span>
              </h3>
              <p className="text-[11px] text-gray-400">
                End-to-end data isolation, private document grounding, and zero model training
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

        {/* Scrollable Body */}
        <div className="px-6 py-5 space-y-5 overflow-y-auto custom-scrollbar text-xs">
          {statusMsg && (
            <div
              className={`p-3 rounded-2xl flex items-center space-x-2.5 ${
                statusMsg.type === 'success'
                  ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-500/15 border border-rose-500/30 text-rose-300'
              }`}
            >
              {statusMsg.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0" />
              )}
              <span>{statusMsg.text}</span>
            </div>
          )}

          {/* Incognito / Temporary Chat Mode Card */}
          <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-between hover:border-emerald-500/30 transition-all">
            <div className="flex items-start space-x-3 pr-4">
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5 ${
                  isIncognito
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'bg-white/[0.05] text-gray-400 border border-white/[0.08]'
                }`}
              >
                <EyeOff className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-white">Incognito / Temporary Chat</span>
                  {isIncognito && (
                    <span className="px-1.5 py-0.5 text-[9px] bg-amber-500/20 text-amber-300 font-bold rounded">
                      ACTIVE
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-gray-400 mt-0.5 leading-relaxed">
                  When enabled, conversations are processed in real-time and will not be saved to your history or database.
                </p>
              </div>
            </div>
            <button
              onClick={() => onToggleIncognito(!isIncognito)}
              className={`px-3 py-1.5 rounded-xl font-semibold text-xs transition-all shrink-0 ${
                isIncognito
                  ? 'bg-amber-500 text-black shadow-lg shadow-amber-500/20 font-bold'
                  : 'bg-white/[0.08] text-gray-300 hover:bg-white/[0.15] hover:text-white'
              }`}
            >
              {isIncognito ? 'Disable' : 'Enable'}
            </button>
          </div>

          {/* Core Privacy Guarantees Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.06] space-y-1.5">
              <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-[11px]">
                <Database className="w-3.5 h-3.5" />
                <span>Isolated Knowledge Vault</span>
              </div>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                Your uploaded documents, text chunks, and vector embeddings are partitioned strictly by your account ID. No other user can search or access your files.
              </p>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.06] space-y-1.5">
              <div className="flex items-center space-x-2 text-teal-400 font-semibold text-[11px]">
                <Lock className="w-3.5 h-3.5" />
                <span>Zero AI Training</span>
              </div>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                Conversations, prompts, and extracted document context are never retained or utilized for training AI models.
              </p>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.06] space-y-1.5">
              <div className="flex items-center space-x-2 text-cyan-400 font-semibold text-[11px]">
                <Server className="w-3.5 h-3.5" />
                <span>Encrypted Session State</span>
              </div>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                Session tokens are signed with cryptographic JWT keys. Your credentials and auth tokens never leave your secured session.
              </p>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.06] space-y-1.5">
              <div className="flex items-center space-x-2 text-purple-400 font-semibold text-[11px]">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Strict Retrieval-Only RAG</span>
              </div>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                Document data is only retrieved when directly relevant to your query and completely excluded when discussing other topics.
              </p>
            </div>
          </div>

          {/* Data Controls & Permanent Purge Actions */}
          <div className="space-y-2 pt-2 border-t border-white/[0.08]">
            <h4 className="font-semibold text-gray-300 text-[11px] uppercase tracking-wider">
              Data Management & Purge Controls
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button
                onClick={handlePurgeAllChats}
                disabled={purgingChats || conversations.length === 0}
                className="p-3 rounded-2xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-300 transition-all flex items-center justify-between group disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <div className="flex items-center space-x-2.5 text-left">
                  <Trash2 className="w-4 h-4 shrink-0 text-rose-400 group-hover:scale-110 transition-transform" />
                  <div>
                    <div className="font-semibold text-[11px]">Purge All Chats</div>
                    <div className="text-[10px] text-gray-400">
                      Delete {conversations.length} conversation{conversations.length === 1 ? '' : 's'}
                    </div>
                  </div>
                </div>
                {purgingChats && <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-400" />}
              </button>

              <button
                onClick={handlePurgeAllDocs}
                disabled={purgingDocs}
                className="p-3 rounded-2xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 text-amber-300 transition-all flex items-center justify-between group disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <div className="flex items-center space-x-2.5 text-left">
                  <FileText className="w-4 h-4 shrink-0 text-amber-400 group-hover:scale-110 transition-transform" />
                  <div>
                    <div className="font-semibold text-[11px]">Wipe All Documents</div>
                    <div className="text-[10px] text-gray-400">Flush files & vector cache</div>
                  </div>
                </div>
                {purgingDocs && <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />}
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-white/[0.08] bg-black/30 flex items-center justify-between">
          <div className="flex items-center space-x-1.5 text-[11px] text-gray-400">
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span>Your data is stored locally and isolated to your account</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-white/[0.08] hover:bg-white/[0.15] text-white font-semibold text-xs rounded-xl transition-all"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
