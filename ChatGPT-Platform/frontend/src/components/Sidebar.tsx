import React, { useState } from 'react';
import { Plus, Search, MessageSquare, Edit2, Trash2, Check, X, FileText, Sparkles, FolderSync, Clock } from 'lucide-react';
import { Conversation } from '../types';

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onDeleteConversation: (id: string) => void;
  onOpenDocumentManager: () => void;
  searchTerm: string;
  onSearchChange: (val: string) => void;
  docCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onRenameConversation,
  onDeleteConversation,
  onOpenDocumentManager,
  searchTerm,
  onSearchChange,
  docCount,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const handleStartRename = (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveRename = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      onRenameConversation(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    onDeleteConversation(id);
  };

  return (
    <aside className="w-68 sm:w-76 h-full bg-[#0b0f19] border-r border-white/[0.08] flex flex-col justify-between select-none z-20 shrink-0 shadow-xl">
      {/* Top Section */}
      <div className="p-3.5 flex flex-col flex-1 overflow-hidden">
        {/* + New Chat Gradient Button */}
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-between px-4 py-3 rounded-2xl bg-gradient-to-r from-white/[0.07] to-white/[0.03] hover:from-white/[0.12] hover:to-white/[0.06] border border-white/[0.1] hover:border-emerald-500/50 text-white font-bold text-sm transition-all shadow-md group active:scale-[0.99]"
        >
          <div className="flex items-center space-x-2.5">
            <div className="w-6 h-6 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
              <Plus className="w-4 h-4" />
            </div>
            <span className="font-bold text-sm tracking-tight">New Chat</span>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded-lg bg-black/40 text-gray-400 border border-white/[0.08] font-mono">
            Ctrl+K
          </span>
        </button>

        {/* Search Bar */}
        <div className="mt-3.5 relative">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search conversations..."
            className="w-full pl-9 pr-3.5 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-emerald-500/60 transition-all focus:bg-white/[0.05]"
          />
          {searchTerm && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Conversation List */}
        <div className="mt-4 flex-1 overflow-y-auto pr-1">
          <div className="text-[10px] font-bold tracking-wider text-gray-400 uppercase px-2 mb-2 flex items-center justify-between">
            <span>Recent Chats</span>
            <Clock className="w-3 h-3 text-gray-400" />
          </div>

          <div className="space-y-1">
            {conversations.length === 0 ? (
              <div className="text-center py-10 text-xs text-gray-400">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                No chats found
              </div>
            ) : (
              conversations.map((conv) => {
                const isActive = conv.id === activeConversationId;
                const isEditing = conv.id === editingId;

                return (
                  <div
                    key={conv.id}
                    onClick={() => onSelectConversation(conv.id)}
                    className={`group relative flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-xs transition-all ${
                      isActive
                        ? 'bg-gradient-to-r from-emerald-500/15 to-teal-500/10 border border-emerald-500/30 text-white shadow-sm font-semibold'
                        : 'text-gray-400 hover:bg-white/[0.04] hover:text-gray-200 border border-transparent'
                    }`}
                  >
                    {isEditing ? (
                      <div className="flex items-center space-x-1 w-full" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveRename(e as any, conv.id);
                            if (e.key === 'Escape') handleCancelRename(e as any);
                          }}
                          autoFocus
                          className="flex-1 bg-[#090d16] text-white text-xs px-2.5 py-1 rounded-lg border border-emerald-500 outline-none"
                        />
                        <button onClick={(e) => handleSaveRename(e, conv.id)} className="p-1 text-emerald-400 hover:scale-110 transition-transform">
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={handleCancelRename} className="p-1 text-rose-400 hover:scale-110 transition-transform">
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center space-x-2.5 truncate pr-2">
                          <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-emerald-400' : 'text-gray-400'}`} />
                          <span className="truncate">{conv.title || 'New Chat'}</span>
                        </div>

                        {/* Action buttons on hover */}
                        <div className={`items-center space-x-1 shrink-0 ${isActive ? 'flex' : 'hidden group-hover:flex'}`}>
                          <button
                            onClick={(e) => handleStartRename(e, conv)}
                            title="Rename chat"
                            className="p-1 text-gray-500 hover:text-white transition-colors rounded"
                          >
                            <Edit2 className="w-3 h-3" />
                          </button>
                          <button
                            onClick={(e) => handleDelete(e, conv.id)}
                            title="Delete chat"
                            className="p-1 text-gray-500 hover:text-rose-400 transition-colors rounded"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Bottom Document Manager (RAG) Button */}
      <div className="p-3.5 border-t border-white/[0.08]">
        <button
          onClick={onOpenDocumentManager}
          className="w-full flex items-center justify-between p-3 rounded-2xl border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.06] hover:border-emerald-500/30 transition-all group"
        >
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
              <FileText className="w-4 h-4" />
            </div>
            <div className="text-left">
              <div className="text-xs font-bold text-gray-200 group-hover:text-white">Document Manager</div>
              <div className="text-[10px] text-emerald-400/80 font-medium">RAG Grounded Q&A</div>
            </div>
          </div>
          <span className="text-[10px] px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 font-mono font-bold border border-emerald-500/30">
            {docCount > 0 ? `${docCount} Docs` : 'PDF/DOCX'}
          </span>
        </button>
      </div>
    </aside>
  );
};
