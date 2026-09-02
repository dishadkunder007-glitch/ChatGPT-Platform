'use client';

import { useRef, useState, useCallback } from 'react';
import { useStore } from '@/lib/store';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { ChatArea } from '@/components/chat/ChatArea';
import { InputBox } from '@/components/chat/InputBox';
import { DocumentModal } from '@/components/modals/DocumentModal';
import { SettingsModal } from '@/components/modals/SettingsModal';
import { AuthModal } from '@/components/modals/AuthModal';
import { ProfileModal } from '@/components/modals/ProfileModal';
import * as api from '@/lib/api';
import { Message } from '@/types';

export default function HomePage() {
  const {
    user, activeConvId, currentModel, temperature, systemPrompt, useRag,
    messages, isStreaming,
    addMessage, updateMessage, setMessages, setStreaming,
    addConversation, updateConversation, setActiveConvId,
    isDocModalOpen, isSettingsOpen, isProfileOpen,
    setDocModalOpen, setSettingsOpen, setProfileOpen,
  } = useStore();

  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSend = useCallback(async (message: string) => {
    if (!message.trim() || isStreaming) return;

    const tempUserMsgId = `user-${Date.now()}`;
    const tempAsstMsgId = `asst-${Date.now()}`;

    // Optimistically add user message
    addMessage({
      id: tempUserMsgId,
      conversation_id: activeConvId || '',
      role: 'user',
      content: message,
    });

    // Add placeholder streaming assistant message
    addMessage({
      id: tempAsstMsgId,
      conversation_id: activeConvId || '',
      role: 'assistant',
      content: '',
      isStreaming: true,
    });

    setStreaming(true);
    abortControllerRef.current = new AbortController();

    try {
      let realAsstMsgId = tempAsstMsgId;
      let realConvId = activeConvId;
      let fullContent = '';

      await api.streamChat({
        message,
        conversationId: activeConvId,
        model: currentModel,
        useRag,
        temperature,
        systemPrompt,
        signal: abortControllerRef.current.signal,

        onStart: (data) => {
          realConvId = data.conversation_id;
          realAsstMsgId = data.assistant_msg_id;

          // Update conversation ID if newly created
          if (!activeConvId && data.conversation_id) {
            setActiveConvId(data.conversation_id);
            // Add the new conversation to the list
            addConversation({
              id: data.conversation_id,
              title: message.slice(0, 50) || 'New Chat',
              model: currentModel,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            });
          } else if (realConvId) {
            updateConversation(realConvId, { updated_at: new Date().toISOString() });
          }

          // Replace temp IDs with real ones
          useStore.getState().updateMessage(tempUserMsgId, { conversation_id: realConvId || '' });
          useStore.getState().updateMessage(tempAsstMsgId, {
            id: realAsstMsgId,
            conversation_id: realConvId || '',
            citations: data.citations,
          });
        },

        onToken: (token) => {
          fullContent += token;
          useStore.getState().updateMessage(realAsstMsgId, { content: fullContent });
        },

        onDone: (content) => {
          useStore.getState().updateMessage(realAsstMsgId, { content, isStreaming: false });
          if (realConvId) {
            updateConversation(realConvId, { preview: content.slice(0, 80) });
          }
        },

        onError: (err) => {
          if (err.name !== 'AbortError') {
            useStore.getState().updateMessage(realAsstMsgId, {
              content: `❌ Error: ${err.message}. Please try again.`,
              isStreaming: false,
            });
          }
        },
      });
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        updateMessage(tempAsstMsgId, {
          content: '❌ Failed to get a response. Please check your connection and try again.',
          isStreaming: false,
        });
      }
    } finally {
      setStreaming(false);
      abortControllerRef.current = null;
    }
  }, [isStreaming, activeConvId, currentModel, useRag, temperature, systemPrompt]);

  function handleStop() {
    abortControllerRef.current?.abort();
    setStreaming(false);
    // Mark last streaming message as done
    const lastMsg = useStore.getState().messages.findLast((m) => m.isStreaming);
    if (lastMsg) {
      updateMessage(lastMsg.id, { isStreaming: false });
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#0f0f0f]">
      {/* Sidebar */}
      <Sidebar
        onAuthOpen={() => setIsAuthOpen(true)}
        onSettingsOpen={() => setSettingsOpen(true)}
        onDocOpen={() => setDocModalOpen(true)}
        onProfileOpen={() => setProfileOpen(true)}
      />

      {/* Main content */}
      <div className="flex flex-col flex-1 min-w-0 h-full">
        <Header
          onSettingsOpen={() => setSettingsOpen(true)}
          onAuthOpen={() => setIsAuthOpen(true)}
          onProfileOpen={() => setProfileOpen(true)}
        />

        <main className="flex flex-col flex-1 overflow-hidden">
          <ChatArea onSendMessage={handleSend} />
          <InputBox onSend={handleSend} onStop={handleStop} />
        </main>
      </div>

      {/* Modals */}
      {isAuthOpen && <AuthModal onClose={() => setIsAuthOpen(false)} />}
      {isDocModalOpen && <DocumentModal onClose={() => setDocModalOpen(false)} />}
      {isSettingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
      {isProfileOpen && <ProfileModal onClose={() => setProfileOpen(false)} />}
    </div>
  );
}
