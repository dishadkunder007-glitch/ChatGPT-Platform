export interface User {
  id: number;
  email: string;
  name: string;
  is_guest: boolean;
  avatar_url?: string | null;
  custom_api_key?: string | null;
  preferred_model?: string;
  system_prompt?: string;
}

export interface Citation {
  citation_id: number;
  filename: string;
  page: number;
  chunk_id: number;
  text: string;
  score: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  model?: string;
  citations?: Citation[] | null;
  feedback?: number; // 0, 1, -1
  created_at?: string;
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  model: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
  preview?: string;
}

export interface ModelOption {
  id: string;
  name: string;
  badge: string;
  provider: string;
  description: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  created_at: string;
}
