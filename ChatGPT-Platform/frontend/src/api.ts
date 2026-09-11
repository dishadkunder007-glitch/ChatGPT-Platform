import {
  User,
  Conversation,
  Message,
  DocumentItem,
  ModelOption,
  Citation,
} from './types';

const API_BASE = (import.meta as any).env?.VITE_API_URL || '/api';

// ─────────────────────────────────────────────
// Authentication token helpers
// ─────────────────────────────────────────────

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return localStorage.getItem('chatgpt_token');
}

export function setAuthToken(token: string): void {
  localStorage.setItem('chatgpt_token', token);
}

export function removeAuthToken(): void {
  localStorage.removeItem('chatgpt_token');
}

// ─────────────────────────────────────────────
// Common API request helper
// ─────────────────────────────────────────────

async function request(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  const token = getAuthToken();

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (
    !(options.body instanceof FormData) &&
    !headers['Content-Type']
  ) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorMsg = 'An error occurred';

    try {
      const errorData = await res.json();

      errorMsg =
        errorData.detail ||
        errorData.message ||
        errorMsg;
    } catch {
      // Keep default error message
    }

    throw new Error(errorMsg);
  }

  return res.json();
}

// ─────────────────────────────────────────────
// Auth API
// ─────────────────────────────────────────────

export async function getGuestUser(): Promise<{
  access_token: string;
  user: User;
}> {
  const data = await request('/auth/guest');

  setAuthToken(data.access_token);

  return data;
}

export async function loginUser(
  email: string,
  password: string
): Promise<{
  access_token: string;
  user: User;
}> {
  const data = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
    }),
  });

  setAuthToken(data.access_token);

  return data;
}

export async function registerUser(
  name: string,
  email: string,
  password: string
): Promise<{
  access_token: string;
  user: User;
}> {
  const data = await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      name,
      email,
      password,
    }),
  });

  setAuthToken(data.access_token);

  return data;
}

export async function googleLogin(
  credential: string,
  name?: string,
  email?: string,
  avatar_url?: string,
  firebase_uid?: string
): Promise<{
  access_token: string;
  user: User;
}> {
  const data = await request('/auth/google', {
    method: 'POST',
    body: JSON.stringify({
      credential,
      name,
      email,
      avatar_url,
      firebase_uid,
    }),
  });

  setAuthToken(data.access_token);

  return data;
}

export async function getCurrentUser(): Promise<User> {
  return request('/auth/me');
}

export async function updateUserProfile(
  profile: Partial<User>
): Promise<any> {
  return request('/auth/profile', {
    method: 'PUT',
    body: JSON.stringify(profile),
  });
}

// ─────────────────────────────────────────────
// Conversations API
// ─────────────────────────────────────────────

export async function getConversations(
  search?: string
): Promise<Conversation[]> {
  const query = search
    ? `?search=${encodeURIComponent(search)}`
    : '';

  return request(`/conversations${query}`);
}

export async function createConversation(
  title?: string,
  model?: string
): Promise<Conversation> {
  return request('/conversations', {
    method: 'POST',
    body: JSON.stringify({
      title: title || 'New Chat',
      model: model || 'qwen2.5:1.5b',
    }),
  });
}

export async function renameConversation(
  id: string,
  title: string
): Promise<any> {
  return request(`/conversations/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      title,
    }),
  });
}

export async function deleteConversation(
  id: string
): Promise<any> {
  return request(`/conversations/${id}`, {
    method: 'DELETE',
  });
}

export async function getMessages(
  conversationId: string
): Promise<Message[]> {
  return request(
    `/conversations/${conversationId}/messages`
  );
}

export async function sendFeedback(
  messageId: string,
  feedback: number
): Promise<any> {
  return request('/chat/feedback', {
    method: 'POST',
    body: JSON.stringify({
      message_id: messageId,
      feedback,
    }),
  });
}

// ─────────────────────────────────────────────
// Models API
// ─────────────────────────────────────────────

export async function getModels(): Promise<ModelOption[]> {
  return request('/models');
}

// ─────────────────────────────────────────────
// Documents & RAG API
// ─────────────────────────────────────────────

export async function getDocuments(): Promise<DocumentItem[]> {
  return request('/documents');
}

export async function uploadDocument(
  file: File
): Promise<DocumentItem> {
  const formData = new FormData();

  formData.append('file', file);

  return request('/documents/upload', {
    method: 'POST',
    body: formData,
  });
}

export async function deleteDocument(
  id: string
): Promise<any> {
  return request(`/documents/${id}`, {
    method: 'DELETE',
  });
}

export async function deleteAllDocuments(): Promise<any> {
  return request('/documents', {
    method: 'DELETE',
  });
}

export async function purgeAllDocuments(): Promise<any> {
  return request('/documents/purge-all', {
    method: 'POST',
  });
}

// ─────────────────────────────────────────────
// Chat API
// ─────────────────────────────────────────────
// The backend now returns normal JSON instead of SSE.
// We keep the name "streamChat" so the existing frontend
// does not need to be changed.
// ─────────────────────────────────────────────

export async function streamChat(
  params: {
    conversationId?: string;
    message: string;
    model?: string;
    temperature?: number;
    systemPrompt?: string;
    useRag?: boolean;
  },
  callbacks: {
    onStart: (data: {
      conversation_id: string;
      assistant_msg_id: string;
      citations?: Citation[];
    }) => void;

    onToken: (token: string) => void;

    onDone: (fullContent: string) => void;

    onError: (error: string) => void;
  },
  signal?: AbortSignal
): Promise<void> {
  const token = getAuthToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers,

      body: JSON.stringify({
        conversation_id: params.conversationId,
        message: params.message,
        model: params.model || 'qwen2.5:1.5b',
        temperature: params.temperature ?? 0.7,
        system_prompt: params.systemPrompt,
        use_rag: params.useRag ?? true,
      }),

      signal,
    });

    if (!res.ok) {
      let errorMsg = 'Chat request failed';

      try {
        const errorData = await res.json();

        errorMsg =
          errorData.detail ||
          errorData.message ||
          errorMsg;
      } catch {
        try {
          const errorText = await res.text();

          if (errorText) {
            errorMsg = errorText;
          }
        } catch {
          // Keep default error message
        }
      }

      callbacks.onError(errorMsg);
      return;
    }

    const data = await res.json();

    callbacks.onStart({
      conversation_id: data.conversation_id,
      assistant_msg_id: data.assistant_msg_id,
      citations: data.citations || [],
    });

    const fullContent: string = data.full_content || '';

    callbacks.onToken(fullContent);

    callbacks.onDone(fullContent);
  } catch (err: unknown) {
    if (
      err instanceof Error &&
      err.name === 'AbortError'
    ) {
      callbacks.onDone('');
      return;
    }

    if (err instanceof Error) {
      callbacks.onError(err.message);
      return;
    }

    callbacks.onError('Chat request failed');
  }
}