'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Conversation, Message, ModelOption, DocumentItem } from '@/types';

interface AppState {
  // Auth
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  // Conversations
  conversations: Conversation[];
  activeConvId: string | null;
  messages: Message[];
  searchTerm: string;

  // AI Settings
  models: ModelOption[];
  currentModel: string;
  temperature: number;
  systemPrompt: string;
  useRag: boolean;

  // Documents
  documents: DocumentItem[];

  // UI state
  isSidebarOpen: boolean;
  isStreaming: boolean;
  isDocModalOpen: boolean;
  isSettingsOpen: boolean;
  isProfileOpen: boolean;

  // Actions
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;

  setConversations: (convs: Conversation[]) => void;
  addConversation: (conv: Conversation) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  removeConversation: (id: string) => void;
  setActiveConvId: (id: string | null) => void;

  setMessages: (msgs: Message[]) => void;
  addMessage: (msg: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  removeMessagesFrom: (fromId: string) => void;

  setModels: (models: ModelOption[]) => void;
  setCurrentModel: (model: string) => void;
  setTemperature: (temp: number) => void;
  setSystemPrompt: (prompt: string) => void;
  setUseRag: (use: boolean) => void;

  setDocuments: (docs: DocumentItem[]) => void;
  addDocument: (doc: DocumentItem) => void;
  removeDocument: (id: string) => void;

  setSearchTerm: (term: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setStreaming: (streaming: boolean) => void;
  setDocModalOpen: (open: boolean) => void;
  setSettingsOpen: (open: boolean) => void;
  setProfileOpen: (open: boolean) => void;
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,

      conversations: [],
      activeConvId: null,
      messages: [],
      searchTerm: '',

      models: [],
      currentModel: 'qwen2.5:1.5b',
      temperature: 0.7,
      systemPrompt: 'You are a helpful AI assistant. Provide clear, accurate, and well-structured responses.',
      useRag: true,

      documents: [],

      isSidebarOpen: true,
      isStreaming: false,
      isDocModalOpen: false,
      isSettingsOpen: false,
      isProfileOpen: false,

      // Auth actions
      setUser: (user) => set((state) => {
        const isDifferentUser = state.user?.id !== user?.id;
        const preferred = user?.preferred_model;
        const validPreferred = preferred && !preferred.toLowerCase().includes('llama') && !preferred.toLowerCase().includes('groq') ? preferred : 'qwen2.5:1.5b';
        return {
          user,
          isAuthenticated: !!user && !user.is_guest,
          currentModel: validPreferred,
          conversations: isDifferentUser ? [] : state.conversations,
          activeConvId: isDifferentUser ? null : state.activeConvId,
          messages: isDifferentUser ? [] : state.messages,
        };
      }),
      setToken: (token) => set({ token }),
      logout: () => set({
        user: null,
        token: null,
        isAuthenticated: false,
        conversations: [],
        activeConvId: null,
        messages: [],
        documents: [],
      }),

      // Conversation actions
      setConversations: (conversations) => set({ conversations }),
      addConversation: (conv) => set((state) => ({
        conversations: [conv, ...state.conversations]
      })),
      updateConversation: (id, updates) => set((state) => ({
        conversations: state.conversations.map((c) =>
          c.id === id ? { ...c, ...updates } : c
        )
      })),
      removeConversation: (id) => set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== id),
        activeConvId: state.activeConvId === id ? null : state.activeConvId,
        messages: state.activeConvId === id ? [] : state.messages,
      })),
      setActiveConvId: (id) => set({ activeConvId: id }),

      // Message actions
      setMessages: (messages) => set({ messages }),
      addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
      updateMessage: (id, updates) => set((state) => ({
        messages: state.messages.map((m) => m.id === id ? { ...m, ...updates } : m)
      })),
      removeMessagesFrom: (fromId) => set((state) => {
        const idx = state.messages.findIndex((m) => m.id === fromId);
        if (idx === -1) return state;
        return { messages: state.messages.slice(0, idx) };
      }),

      // Model/settings actions
      setModels: (models) => set({ models }),
      setCurrentModel: (currentModel) => set({ currentModel }),
      setTemperature: (temperature) => set({ temperature }),
      setSystemPrompt: (systemPrompt) => set({ systemPrompt }),
      setUseRag: (useRag) => set({ useRag }),

      // Document actions
      setDocuments: (documents) => set({ documents }),
      addDocument: (doc) => set((state) => ({ documents: [doc, ...state.documents] })),
      removeDocument: (id) => set((state) => ({
        documents: state.documents.filter((d) => d.id !== id)
      })),

      // UI actions
      setSearchTerm: (searchTerm) => set({ searchTerm }),
      setSidebarOpen: (isSidebarOpen) => set({ isSidebarOpen }),
      setStreaming: (isStreaming) => set({ isStreaming }),
      setDocModalOpen: (isDocModalOpen) => set({ isDocModalOpen }),
      setSettingsOpen: (isSettingsOpen) => set({ isSettingsOpen }),
      setProfileOpen: (isProfileOpen) => set({ isProfileOpen }),
    }),
    {
      name: 'chatgpt-platform-store',
      // Only persist auth info and preferences
      partialize: (state) => ({
        token: state.token,
        currentModel: state.currentModel,
        temperature: state.temperature,
        systemPrompt: state.systemPrompt,
        useRag: state.useRag,
        isSidebarOpen: state.isSidebarOpen,
      }),
    }
  )
);
