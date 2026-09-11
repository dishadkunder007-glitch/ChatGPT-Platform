import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { InputBox } from './components/InputBox';
import { DocumentModal } from './components/DocumentModal';
import { SettingsModal } from './components/SettingsModal';
import { AuthModal } from './components/AuthModal';
import { PrivacyModal } from './components/PrivacyModal';
import { User, Conversation, Message, ModelOption, DocumentItem } from './types';
import {
  getCurrentUser,
  getGuestUser,
  getConversations,
  createConversation,
  renameConversation,
  deleteConversation,
  getMessages,
  getModels,
  getDocuments,
  uploadDocument,
  deleteDocument,
  deleteAllDocuments,
  streamChat,
  sendFeedback,
  removeAuthToken,
} from './api';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [currentModel, setCurrentModel] = useState<string>('qwen2.5:1.5b');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [systemPrompt, setSystemPrompt] = useState('You are ChatGPT. Always answer questions in simple, plain words using well-structured, easy-to-read paragraphs without complex symbols.');
  const [isIncognito, setIsIncognito] = useState(false);

  // Modals
  const [isDocModalOpen, setIsDocModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Initialize App
  useEffect(() => {
    async function init() {
      try {
        let currentUser: User;
        try {
          currentUser = await getCurrentUser();
        } catch {
          const res = await getGuestUser();
          currentUser = res.user;
        }
        setUser(currentUser);
        if (
          currentUser.preferred_model &&
          !currentUser.preferred_model.toLowerCase().includes('llama') &&
          !currentUser.preferred_model.toLowerCase().includes('groq')
        ) {
          setCurrentModel(currentUser.preferred_model);
        } else {
          setCurrentModel('qwen2.5:1.5b');
        }
        if (currentUser.system_prompt) setSystemPrompt(currentUser.system_prompt);

        // Fetch models
        const modelList = await getModels();
        const filteredModels = modelList.filter(
          (m) =>
            !m.id.toLowerCase().includes('llama') &&
            !m.id.toLowerCase().includes('groq') &&
            !m.name.toLowerCase().includes('llama')
        );
        const hasQwen = filteredModels.some((m) => m.id === 'qwen2.5:1.5b');
        const updatedModels: ModelOption[] = hasQwen
          ? filteredModels
          : [
              {
                id: 'qwen2.5:1.5b',
                name: 'Qwen 2.5 1.5B',
                badge: 'Ollama',
                provider: 'Ollama',
                description: 'Local Ollama engine running Qwen 2.5 1.5B model.',
              },
              ...filteredModels,
            ];
        setModels(updatedModels);

        // Fetch conversations
        const convList = await getConversations();
        setConversations(convList);
        if (convList.length > 0) {
          setActiveConvId(convList[0].id);
          const msgs = await getMessages(convList[0].id);
          setMessages(msgs);
        }

        // Fetch documents
        const docList = await getDocuments();
        setDocuments(docList);
      } catch (err) {
        console.error('Initialization error:', err);
      }
    }
    init();
  }, []);

  // Keyboard shortcut: Ctrl+K for New Chat
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        handleNewChat();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentModel]);

  // Load messages when active conversation changes
  const handleSelectConversation = async (id: string) => {
    setActiveConvId(id);
    try {
      const msgs = await getMessages(id);
      setMessages(msgs);
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  };

  // Create New Chat
  const handleNewChat = async () => {
    try {
      const newConv = await createConversation('New Chat', currentModel || 'qwen2.5:1.5b');
      setConversations((prev) => [newConv, ...prev]);
      setActiveConvId(newConv.id);
      setMessages([]);
      setInput('');
    } catch (err) {
      console.error('Failed to create new conversation:', err);
    }
  };

  // Rename Conversation
  const handleRenameConversation = async (id: string, newTitle: string) => {
    try {
      await renameConversation(id, newTitle);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
      );
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    }
  };

  // Delete Conversation
  const handleDeleteConversation = async (id: string) => {
    try {
      await deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (activeConvId === id) {
        if (remaining.length > 0) {
          handleSelectConversation(remaining[0].id);
        } else {
          setActiveConvId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  // Send Message & Stream
  const handleSendMessage = async (customMessage?: string) => {
    const textToSend = customMessage || input.trim();
    if (!textToSend || isStreaming) return;

    setInput('');
    setIsStreaming(true);

    const userMsgId = `temp-user-${Date.now()}`;
    const assistantMsgId = `temp-assistant-${Date.now()}`;

    const newMessages: Message[] = [
      ...messages,
      {
        id: userMsgId,
        conversation_id: activeConvId || '',
        role: 'user',
        content: textToSend,
        created_at: new Date().toISOString(),
      },
      {
        id: assistantMsgId,
        conversation_id: activeConvId || '',
        role: 'assistant',
        content: '',
        model: currentModel || 'qwen2.5:1.5b',
        isStreaming: true,
        created_at: new Date().toISOString(),
      },
    ];

    setMessages(newMessages);
    abortControllerRef.current = new AbortController();

    await streamChat(
      {
        conversationId: activeConvId || undefined,
        message: textToSend,
        model: currentModel || 'qwen2.5:1.5b',
        temperature,
        systemPrompt,
        useRag,
      },
      {
        onStart: (data) => {
          if (!activeConvId || activeConvId !== data.conversation_id) {
            setActiveConvId(data.conversation_id);
            getConversations().then(setConversations);
          }
          if (data.citations) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, citations: data.citations }
                  : m
              )
            );
          }
        },
        onToken: (token) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: m.content + token }
                : m
            )
          );
        },
        onDone: (fullContent) => {
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: fullContent || m.content, isStreaming: false }
                : m
            )
          );
          getConversations().then(setConversations);
        },
        onError: (err) => {
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    content: m.content + `\n\n*(Error: ${err})*`,
                    isStreaming: false,
                  }
                : m
            )
          );
        },
      },
      abortControllerRef.current.signal
    );
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      setMessages((prev) =>
        prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m))
      );
    }
  };

  const handleRegenerate = (assistantMsgId: string) => {
    const assistantIdx = messages.findIndex((m) => m.id === assistantMsgId);
    if (assistantIdx > 0 && messages[assistantIdx - 1].role === 'user') {
      const userPrompt = messages[assistantIdx - 1].content;
      setMessages((prev) => prev.slice(0, assistantIdx));
      handleSendMessage(userPrompt);
    }
  };

  const handleEditMessage = (msgId: string, newContent: string) => {
    const msgIdx = messages.findIndex((m) => m.id === msgId);
    if (msgIdx !== -1) {
      setMessages((prev) => prev.slice(0, msgIdx));
      handleSendMessage(newContent);
    }
  };

  const handleFeedback = async (messageId: string, feedback: number) => {
    try {
      await sendFeedback(messageId, feedback);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, feedback } : m))
      );
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  const handleLogout = async () => {
    removeAuthToken();
    const guest = await getGuestUser();
    setUser(guest.user);
    const convList = await getConversations();
    setConversations(convList);
    if (convList.length > 0) {
      handleSelectConversation(convList[0].id);
    } else {
      setMessages([]);
    }
  };

  const refreshDocuments = async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    try {
      await deleteDocument(docId);
      await refreshDocuments();
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const handleUploadDocument = async (file: File) => {
    try {
      await uploadDocument(file);
      await refreshDocuments();
    } catch (err) {
      console.error('Failed to upload document:', err);
    }
  };

  const handleClearAllDocuments = async () => {
    if (!window.confirm('Are you sure you want to delete ALL uploaded documents? This will completely clear the RAG knowledge base.')) {
      return;
    }
    try {
      await deleteAllDocuments();
      await refreshDocuments();
    } catch (err) {
      console.error('Failed to clear all documents:', err);
    }
  };

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex h-screen w-screen bg-[#090d16] text-[#e6edf3] font-sans overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        conversations={filteredConversations}
        activeConversationId={activeConvId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onRenameConversation={handleRenameConversation}
        onDeleteConversation={handleDeleteConversation}
        onOpenDocumentManager={() => setIsDocModalOpen(true)}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        docCount={documents.length}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#090d16] relative">
        {/* Header Bar */}
        <Header
          currentModel={currentModel}
          onSelectModel={(m) => setCurrentModel(m)}
          models={models}
          user={user}
          onNewChat={handleNewChat}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onOpenPrivacy={() => setIsPrivacyOpen(true)}
          onOpenAuth={() => setIsAuthOpen(true)}
          onLogout={handleLogout}
          isIncognito={isIncognito}
        />

        {/* Chat Messages */}
        <ChatArea
          messages={messages}
          isStreaming={isStreaming}
          onRegenerate={handleRegenerate}
          onEditMessage={handleEditMessage}
          onFeedback={handleFeedback}
          onSelectPrompt={(text) => handleSendMessage(text)}
          userName={user?.name}
        />

        {/* Input Bar */}
        <InputBox
          input={input}
          setInput={setInput}
          onSend={() => handleSendMessage()}
          onStop={handleStopGeneration}
          isStreaming={isStreaming}
          onOpenDocumentManager={() => setIsDocModalOpen(true)}
          attachedDocsCount={documents.length}
          useRag={useRag}
          documents={documents}
          onDeleteDocument={handleDeleteDocument}
          onUploadFile={handleUploadDocument}
          onClearAllDocuments={handleClearAllDocuments}
        />
      </div>

      {/* Modals */}
      <PrivacyModal
        isOpen={isPrivacyOpen}
        onClose={() => setIsPrivacyOpen(false)}
        conversations={conversations}
        onConversationsPurged={() => {
          setConversations([]);
          setMessages([]);
          setActiveConvId(null);
        }}
        onDocumentsPurged={refreshDocuments}
        isIncognito={isIncognito}
        onToggleIncognito={(val) => setIsIncognito(val)}
      />

      <DocumentModal
        isOpen={isDocModalOpen}
        onClose={() => setIsDocModalOpen(false)}
        documents={documents}
        onDocumentsUpdated={refreshDocuments}
        useRag={useRag}
        setUseRag={setUseRag}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        user={user}
        models={models}
        currentModel={currentModel}
        onSelectModel={setCurrentModel}
        temperature={temperature}
        setTemperature={setTemperature}
        systemPrompt={systemPrompt}
        setSystemPrompt={setSystemPrompt}
        onUserUpdated={(updated) => setUser((prev) => (prev ? { ...prev, ...updated } : null))}
      />

      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onSuccess={async (newUser) => {
          setUser(newUser);
          const convList = await getConversations();
          setConversations(convList);
          if (convList.length > 0) {
            handleSelectConversation(convList[0].id);
          }
        }}
      />
    </div>
  );
};

export default App;
