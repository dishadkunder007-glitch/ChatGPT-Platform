'use client';

import { useState, useEffect, useRef } from 'react';
import { useStore } from '@/lib/store';
import * as api from '@/lib/api';
import { signOutFirebase } from '@/lib/firebase';
import {
  Plus, Search, MessageSquare, Pencil, Trash2, Check, X,
  LogIn, LogOut, Settings, FileText, UserCircle2, UserPlus
} from 'lucide-react';
import { Conversation } from '@/types';
import { cn } from '@/lib/utils';

function groupConversations(convs: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const lastWeek = new Date(today.getTime() - 7 * 86400000);
  const lastMonth = new Date(today.getTime() - 30 * 86400000);

  const groups: Record<string, Conversation[]> = {
    Today: [],
    Yesterday: [],
    'Previous 7 Days': [],
    'Previous 30 Days': [],
    Older: [],
  };

  for (const c of convs) {
    const d = new Date(c.updated_at);
    if (d >= today) groups['Today'].push(c);
    else if (d >= yesterday) groups['Yesterday'].push(c);
    else if (d >= lastWeek) groups['Previous 7 Days'].push(c);
    else if (d >= lastMonth) groups['Previous 30 Days'].push(c);
    else groups['Older'].push(c);
  }

  return Object.entries(groups).filter(([, v]) => v.length > 0);
}

interface SidebarProps {
  onAuthOpen: () => void;
  onSettingsOpen: () => void;
  onDocOpen: () => void;
  onProfileOpen: () => void;
}

export function Sidebar({ onAuthOpen, onSettingsOpen, onDocOpen, onProfileOpen }: SidebarProps) {
  const {
    user, conversations, activeConvId, searchTerm, isSidebarOpen,
    setConversations, addConversation, updateConversation, removeConversation,
    setActiveConvId, setMessages, setSearchTerm, setSidebarOpen, logout,
  } = useStore();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isLoggedIn = user && !user.is_guest;

  useEffect(() => {
    loadConversations();
  }, [user?.id]);

  async function loadConversations(search?: string) {
    try {
      const convs = await api.getConversations(search);
      setConversations(convs);
    } catch { }
  }

  function handleSearch(term: string) {
    setSearchTerm(term);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(() => loadConversations(term || undefined), 300);
  }

  async function handleNewChat() {
    try {
      const conv = await api.createConversation('New Chat');
      addConversation(conv);
      setActiveConvId(conv.id);
      setMessages([]);
    } catch { }
  }

  async function selectConversation(id: string) {
    setActiveConvId(id);
    try {
      const msgs = await api.getMessages(id);
      setMessages(msgs);
    } catch { }
  }

  async function handleRename(id: string) {
    if (!editValue.trim()) { setEditingId(null); return; }
    try {
      await api.renameConversation(id, editValue.trim());
      updateConversation(id, { title: editValue.trim() });
    } catch { }
    setEditingId(null);
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteConversation(id);
      removeConversation(id);
      if (activeConvId === id) setMessages([]);
    } catch { }
    setConfirmDeleteId(null);
  }

  async function handleLogout() {
    try {
      await signOutFirebase();
    } catch { }
    logout();
    api.removeToken();
    localStorage.removeItem('auth_token');
    window.location.reload();
  }

  const grouped = groupConversations(conversations);

  return (
    <>
      {/* Mobile overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 h-full z-40 flex flex-col bg-[#171717] transition-all duration-300',
          'w-[260px]',
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full',
          'lg:relative lg:translate-x-0',
          !isSidebarOpen && 'lg:w-0 lg:overflow-hidden'
        )}
      >
        {/* ═══════════════════════════════════════════════
            TOP SECTION: Login/Sign Up OR User Profile
        ═══════════════════════════════════════════════ */}
        {isLoggedIn ? (
          /* Logged-in user chip — top left */
          <div className="flex items-center justify-between px-3 py-3 border-b border-[#2d2d2d]">
            <button
              onClick={onProfileOpen}
              className="flex items-center gap-2.5 min-w-0 hover:opacity-80 transition-opacity"
            >
              {user.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-7 h-7 rounded-full object-cover flex-shrink-0" />
              ) : (
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
                  {user.name.charAt(0).toUpperCase()}
                </div>
              )}
              <div className="min-w-0">
                <p className="text-sm font-semibold text-white truncate leading-tight">{user.name}</p>
                <p className="text-xs text-gray-500 truncate leading-tight">{user.email}</p>
              </div>
            </button>

            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                onClick={handleNewChat}
                className="p-1.5 rounded-lg hover:bg-[#2d2d2d] text-gray-400 hover:text-white transition-colors"
                title="New Chat"
              >
                <Plus size={16} />
              </button>
              <button
                onClick={handleLogout}
                className="p-1.5 rounded-lg hover:bg-[#2d2d2d] text-gray-400 hover:text-red-400 transition-colors"
                title="Logout"
              >
                <LogOut size={15} />
              </button>
            </div>
          </div>
        ) : (
          /* Clean New Chat header for Guest (No Login/Signup buttons in left top corner) */
          <div className="px-3 py-3 border-b border-[#2d2d2d]">
            <button
              onClick={handleNewChat}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg bg-[#212121] hover:bg-[#2d2d2d] border border-[#333] text-white text-sm font-medium transition-colors"
            >
              <Plus size={16} className="text-emerald-400" />
              <span>New chat</span>
            </button>
          </div>
        )}

        {/* Search */}
        <div className="px-3 py-2">
          <div className="flex items-center gap-2 bg-[#2d2d2d] rounded-lg px-3 py-2">
            <Search size={14} className="text-gray-500 flex-shrink-0" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="bg-transparent text-sm text-white placeholder-gray-500 outline-none flex-1 min-w-0"
            />
            {searchTerm && (
              <button onClick={() => handleSearch('')} className="text-gray-500 hover:text-white">
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Conversation list */}
        <nav className="flex-1 overflow-y-auto px-2 pb-2">
          {grouped.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-600 text-sm gap-2">
              <MessageSquare size={22} className="opacity-40" />
              <span>No conversations yet</span>
            </div>
          ) : (
            grouped.map(([label, convs]) => (
              <div key={label} className="mb-2">
                <p className="text-xs text-gray-500 px-2 py-1 font-medium">{label}</p>
                {convs.map((conv) => (
                  <div
                    key={conv.id}
                    className="relative group"
                    onMouseEnter={() => setHoveredId(conv.id)}
                    onMouseLeave={() => setHoveredId(null)}
                  >
                    {editingId === conv.id ? (
                      <div className="flex items-center gap-1 px-2 py-1">
                        <input
                          autoFocus
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleRename(conv.id);
                            if (e.key === 'Escape') setEditingId(null);
                          }}
                          className="flex-1 bg-[#2d2d2d] text-white text-sm px-2 py-1 rounded outline-none border border-emerald-500/50"
                        />
                        <button onClick={() => handleRename(conv.id)} className="text-emerald-400 hover:text-emerald-300 p-1">
                          <Check size={14} />
                        </button>
                        <button onClick={() => setEditingId(null)} className="text-gray-400 hover:text-white p-1">
                          <X size={14} />
                        </button>
                      </div>
                    ) : confirmDeleteId === conv.id ? (
                      <div className="flex items-center justify-between px-2 py-2 rounded-lg bg-red-500/10 border border-red-500/30">
                        <span className="text-xs text-red-400">Delete chat?</span>
                        <div className="flex gap-1">
                          <button onClick={() => handleDelete(conv.id)} className="text-xs text-red-400 hover:text-red-300 px-2 py-0.5 rounded">Yes</button>
                          <button onClick={() => setConfirmDeleteId(null)} className="text-xs text-gray-400 hover:text-white px-2 py-0.5 rounded">No</button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => selectConversation(conv.id)}
                        className={cn(
                          'w-full text-left flex items-center gap-2 px-2 py-2 rounded-lg text-sm transition-colors',
                          activeConvId === conv.id
                            ? 'bg-[#2d2d2d] text-white'
                            : 'text-gray-300 hover:bg-[#252525] hover:text-white'
                        )}
                      >
                        <MessageSquare size={13} className="flex-shrink-0 text-gray-500" />
                        <span className="flex-1 truncate">{conv.title}</span>

                        <div className={cn(
                          'flex gap-0.5 flex-shrink-0 transition-opacity',
                          hoveredId === conv.id || activeConvId === conv.id ? 'opacity-100' : 'opacity-0'
                        )}>
                          <span
                            role="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingId(conv.id);
                              setEditValue(conv.title);
                            }}
                            className="p-1 rounded hover:bg-[#3d3d3d] text-gray-400 hover:text-white cursor-pointer"
                          >
                            <Pencil size={12} />
                          </span>
                          <span
                            role="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmDeleteId(conv.id);
                            }}
                            className="p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 cursor-pointer"
                          >
                            <Trash2 size={12} />
                          </span>
                        </div>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ))
          )}
        </nav>

        {/* Bottom actions */}
        <div className="border-t border-[#2d2d2d] p-2 space-y-1">
          <button
            onClick={onDocOpen}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-[#2d2d2d] hover:text-white transition-colors"
          >
            <FileText size={16} />
            My Documents
          </button>
          <button
            onClick={onSettingsOpen}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-[#2d2d2d] hover:text-white transition-colors"
          >
            <Settings size={16} />
            Settings
          </button>
        </div>
      </aside>
    </>
  );
}
