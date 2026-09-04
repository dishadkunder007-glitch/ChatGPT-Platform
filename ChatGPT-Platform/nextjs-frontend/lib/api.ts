import { User, Conversation, Message, DocumentItem, ModelOption, Citation } from '@/types';

export function getApiUrl(endpoint: string): string {
  if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
    return endpoint;
  }

  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

  // Public backend for the deployed Vercel website
  const baseUrl =
    typeof window !== 'undefined'
      ? 'https://hypothesis-thorough-impacts-posing.trycloudflare.com'
      : (process.env.NEXT_PUBLIC_API_URL ||
        'http://127.0.0.1:8001');

  return `${baseUrl.replace(/\/$/, '')}/api${cleanEndpoint}`;
}

let inMemoryToken: string | null = null;

export function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token') || inMemoryToken;
  }
  return inMemoryToken;
}

export function setToken(token: string) {
  inMemoryToken = token;
  if (typeof window !== 'undefined') {
    localStorage.setItem('auth_token', token);
  }
}

export function removeToken() {
  inMemoryToken = null;
  if (typeof window !== 'undefined') {
    localStorage.removeItem('auth_token');
  }
}

async function request(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const primaryUrl = getApiUrl(endpoint);

  let res: Response;
  try {
    res = await fetch(primaryUrl, {
      ...options,
      headers,
    });
  } catch (err: any) {
    // If the primary fetch failed (e.g. proxy failure or direct connect failure), try fallback
    if (typeof window !== 'undefined') {
      try {
        const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
        const fallbackUrl = primaryUrl.startsWith('http')
          ? `/api${cleanEndpoint}`
          : `http://127.0.0.1:8000/api${cleanEndpoint}`;
        res = await fetch(fallbackUrl, {
          ...options,
          headers,
        });
      } catch {
        throw new Error('Unable to connect to the backend server. Please make sure the backend is running at http://127.0.0.1:8000.');
      }
    } else {
      throw err;
    }
  }

  if (!res.ok) {
    let errorMsg = `Request failed (${res.status})`;
    try {
      const errData = await res.json();
      errorMsg = errData.detail || errData.message || errorMsg;
    } catch {
      // keep fallback
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth API
// ─────────────────────────────────────────────────────────────────────────────
export async function getGuestUser(): Promise<{ access_token: string; user: User }> {
  return request('/auth/guest');
}

export async function login(email: string, password: string): Promise<{ access_token: string; user: User }> {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function register(email: string, name: string, password: string): Promise<{ access_token: string; user: User }> {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, name, password }),
  });
}

export async function googleAuth(
  credential?: string,
  email?: string,
  name?: string,
  avatarUrl?: string,
  firebaseUid?: string
): Promise<{ access_token: string; user: User }> {
  return request('/auth/google', {
    method: 'POST',
    body: JSON.stringify({
      credential: credential || '',
      email,
      name,
      avatar_url: avatarUrl,
      firebase_uid: firebaseUid,
    }),
  });
}

export async function getCurrentUser(): Promise<User> {
  return request('/auth/me');
}

export async function updateProfile(profile: Partial<User>): Promise<any> {
  return request('/auth/profile', {
    method: 'PUT',
    body: JSON.stringify(profile),
  });
}

export async function requestPasswordReset(email: string): Promise<any> {
  return request('/auth/reset-password/request', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export async function confirmPasswordReset(token: string, newPassword: string): Promise<any> {
  return request('/auth/reset-password/confirm', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<any> {
  return request('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export async function deleteAccount(): Promise<any> {
  return request('/auth/account', {
    method: 'DELETE',
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Conversations API
// ─────────────────────────────────────────────────────────────────────────────
export async function getConversations(search?: string): Promise<Conversation[]> {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  return request(`/conversations${query}`);
}

export async function createConversation(title?: string, model?: string): Promise<Conversation> {
  return request('/conversations', {
    method: 'POST',
    body: JSON.stringify({ title: title || 'New Chat', model: model || 'qwen2.5:1.5b' }),
  });
}

export async function renameConversation(id: string, title: string): Promise<any> {
  return request(`/conversations/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversation(id: string): Promise<any> {
  return request(`/conversations/${id}`, {
    method: 'DELETE',
  });
}

export async function getMessages(conversationId: string): Promise<Message[]> {
  return request(`/conversations/${conversationId}/messages`);
}

export async function sendFeedback(messageId: string, feedback: number): Promise<any> {
  return request('/chat/feedback', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, feedback }),
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Models API
// ─────────────────────────────────────────────────────────────────────────────
export async function getModels(): Promise<ModelOption[]> {
  return request('/models');
}

// ─────────────────────────────────────────────────────────────────────────────
// Documents & RAG API
// ─────────────────────────────────────────────────────────────────────────────
export async function getDocuments(): Promise<DocumentItem[]> {
  return request('/documents');
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append('file', file);
  return request('/documents/upload', {
    method: 'POST',
    body: formData,
  });
}

export async function deleteDocument(id: string): Promise<any> {
  return request(`/documents/${id}`, {
    method: 'DELETE',
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Streaming Chat API (SSE)
// ─────────────────────────────────────────────────────────────────────────────
export async function streamChat(
  params: {
    conversationId?: string | null;
    message: string;
    model?: string;
    temperature?: number;
    systemPrompt?: string;
    useRag?: boolean;
    onStart?: (data: { conversation_id: string; assistant_msg_id: string; citations?: Citation[] }) => void;
    onToken?: (token: string) => void;
    onDone?: (fullContent: string) => void;
    onError?: (error: any) => void;
    signal?: AbortSignal;
  }
) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(getApiUrl('/chat/stream'), {
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
      signal: params.signal,
    });

    if (!res.ok) {
      let errDetail = 'Stream connection failed';
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errDetail;
      } catch {
        // keep fallback
      }
      params.onError?.(new Error(errDetail));
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      params.onError?.(new Error('ReadableStream not supported in this browser.'));
      return;
    }

    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;
        const jsonStr = trimmed.slice(6);
        try {
          const payload = JSON.parse(jsonStr);
          if (payload.type === 'start') {
            params.onStart?.(payload);
          } else if (payload.type === 'token') {
            params.onToken?.(payload.token);
          } else if (payload.type === 'done') {
            params.onDone?.(payload.full_content);
          } else if (payload.type === 'error') {
            params.onError?.(new Error(payload.error || 'Chat streaming error'));
          }
        } catch {
          // ignore partial json
        }
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      params.onDone?.('');
    } else {
      params.onError?.(err);
    }
  }
}

export async function streamRegenerate(
  params: {
    conversationId: string;
    messageId: string;
    model?: string;
    temperature?: number;
    systemPrompt?: string;
    onStart?: (data: { assistant_msg_id: string }) => void;
    onToken?: (token: string) => void;
    onDone?: (fullContent: string) => void;
    onError?: (error: any) => void;
    signal?: AbortSignal;
  }
) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(getApiUrl('/chat/regenerate'), {
      method: 'POST',
      headers,
      body: JSON.stringify({
        conversation_id: params.conversationId,
        message_id: params.messageId,
        model: params.model,
        temperature: params.temperature ?? 0.7,
        system_prompt: params.systemPrompt,
      }),
      signal: params.signal,
    });

    if (!res.ok) {
      let errDetail = 'Regeneration failed';
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errDetail;
      } catch {
        // fallback
      }
      params.onError?.(new Error(errDetail));
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;
        const jsonStr = trimmed.slice(6);
        try {
          const payload = JSON.parse(jsonStr);
          if (payload.type === 'start') {
            params.onStart?.(payload);
          } else if (payload.type === 'token') {
            params.onToken?.(payload.token);
          } else if (payload.type === 'done') {
            params.onDone?.(payload.full_content);
          }
        } catch {
          // ignore
        }
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      params.onDone?.('');
    } else {
      params.onError?.(err);
    }
  }
}

export async function streamEdit(
  params: {
    conversationId: string;
    messageId: string;
    newContent: string;
    model?: string;
    temperature?: number;
    systemPrompt?: string;
    onToken?: (token: string) => void;
    onDone?: (fullContent: string) => void;
    onError?: (error: any) => void;
    signal?: AbortSignal;
  }
) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(getApiUrl('/chat/edit'), {
      method: 'POST',
      headers,
      body: JSON.stringify({
        conversation_id: params.conversationId,
        message_id: params.messageId,
        new_content: params.newContent,
        model: params.model,
        temperature: params.temperature ?? 0.7,
        system_prompt: params.systemPrompt,
      }),
      signal: params.signal,
    });

    if (!res.ok) {
      let errDetail = 'Edit stream failed';
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errDetail;
      } catch {
        // fallback
      }
      params.onError?.(new Error(errDetail));
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;
        const jsonStr = trimmed.slice(6);
        try {
          const payload = JSON.parse(jsonStr);
          if (payload.type === 'token') {
            params.onToken?.(payload.token);
          } else if (payload.type === 'done') {
            params.onDone?.(payload.full_content);
          }
        } catch {
          // ignore
        }
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      params.onDone?.('');
    } else {
      params.onError?.(err);
    }
  }
}
