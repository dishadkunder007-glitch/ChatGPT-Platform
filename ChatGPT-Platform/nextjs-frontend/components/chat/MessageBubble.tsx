'use client';

import { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  Copy, Check, RotateCcw, ThumbsUp, ThumbsDown, Pencil, User, Bot,
  ChevronDown, ChevronUp, BookOpen
} from 'lucide-react';
import { Message, Citation } from '@/types';
import { useStore } from '@/lib/store';
import * as api from '@/lib/api';
import { cn } from '@/lib/utils';

interface MessageBubbleProps {
  message: Message;
  isLast: boolean;
}

export function MessageBubble({ message, isLast }: MessageBubbleProps) {
  const { isStreaming, currentModel, temperature, systemPrompt, updateMessage, setMessages, messages } = useStore();
  const [copied, setCopied] = useState(false);
  const [codeCopied, setCodeCopied] = useState<Record<string, boolean>>({});
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [showCitations, setShowCitations] = useState(false);
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  async function copyToClipboard(text: string, id?: string) {
    await navigator.clipboard.writeText(text);
    if (id) {
      setCodeCopied((prev) => ({ ...prev, [id]: true }));
      setTimeout(() => setCodeCopied((prev) => ({ ...prev, [id]: false })), 2000);
    } else {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  async function handleFeedback(feedback: 1 | -1) {
    const newFeedback = message.feedback === feedback ? 0 : feedback;
    try {
      await api.sendFeedback(message.id, newFeedback);
      updateMessage(message.id, { feedback: newFeedback });
    } catch { }
  }

  async function handleRegenerate() {
    if (isStreaming) return;
    const store = useStore.getState();
    const abortController = new AbortController();

    // Remove this message from store, add empty streaming message
    const newMsgId = `streaming-${Date.now()}`;
    const filtered = messages.filter((m) => m.id !== message.id);
    store.setMessages([...filtered, {
      id: newMsgId,
      conversation_id: message.conversation_id,
      role: 'assistant',
      content: '',
      isStreaming: true,
    }]);
    store.setStreaming(true);

    try {
      let fullContent = '';
      await api.streamRegenerate({
        conversationId: message.conversation_id,
        messageId: message.id,
        model: currentModel,
        temperature,
        systemPrompt,
        onStart: (data) => {
          store.updateMessage(newMsgId, { id: data.assistant_msg_id });
        },
        onToken: (token) => {
          fullContent += token;
          store.updateMessage(newMsgId, { content: fullContent });
        },
        onDone: (content) => {
          store.updateMessage(newMsgId, { content, isStreaming: false });
        },
        signal: abortController.signal,
      });
    } catch (e) {
      store.updateMessage(newMsgId, { content: 'Regeneration failed. Please try again.', isStreaming: false });
    } finally {
      store.setStreaming(false);
    }
  }

  async function handleEditSubmit() {
    if (!editContent.trim() || isStreaming) return;
    setIsEditing(false);
    const store = useStore.getState();

    // Remove this message and all after, add edited + new streaming assistant msg
    const thisIdx = messages.findIndex((m) => m.id === message.id);
    const before = messages.slice(0, thisIdx);
    const editedMsg = { ...message, content: editContent };
    const streamingId = `streaming-${Date.now()}`;
    const streamingMsg: Message = {
      id: streamingId,
      conversation_id: message.conversation_id,
      role: 'assistant',
      content: '',
      isStreaming: true,
    };
    store.setMessages([...before, editedMsg, streamingMsg]);
    store.setStreaming(true);

    try {
      let fullContent = '';
      await api.streamEdit({
        conversationId: message.conversation_id,
        messageId: message.id,
        newContent: editContent,
        model: currentModel,
        temperature,
        systemPrompt,
        onToken: (token) => {
          fullContent += token;
          store.updateMessage(streamingId, { content: fullContent });
        },
        onDone: (content) => {
          store.updateMessage(streamingId, { content, isStreaming: false });
        },
      });
    } catch {
      store.updateMessage(streamingId, { content: 'Edit failed. Please try again.', isStreaming: false });
    } finally {
      store.setStreaming(false);
    }
  }

  // Code block renderer with copy button
  const CodeBlock = useCallback(({ node, inline, className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '');
    const lang = match ? match[1] : 'text';
    const code = String(children).replace(/\n$/, '');
    const codeId = `code-${code.slice(0, 20)}`;

    if (inline) {
      return (
        <code className="bg-[#2d2d2d] px-1.5 py-0.5 rounded text-emerald-400 text-sm font-mono" {...props}>
          {children}
        </code>
      );
    }

    return (
      <div className="relative rounded-lg overflow-hidden border border-[#3d3d3d] my-3">
        <div className="flex items-center justify-between bg-[#1a1a1a] px-4 py-2 border-b border-[#3d3d3d]">
          <span className="text-xs text-gray-400 font-mono">{lang}</span>
          <button
            onClick={() => copyToClipboard(code, codeId)}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
          >
            {codeCopied[codeId] ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            {codeCopied[codeId] ? 'Copied!' : 'Copy code'}
          </button>
        </div>
        <SyntaxHighlighter
          style={oneDark}
          language={lang}
          PreTag="div"
          customStyle={{
            margin: 0,
            borderRadius: 0,
            background: '#0f0f0f',
            fontSize: '0.875rem',
            padding: '1rem',
          }}
          {...props}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    );
  }, [codeCopied]);

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 message-fade-in">
        <div className="max-w-[80%] flex gap-3 items-start">
          <div className="bg-[#2d2d2d] rounded-2xl rounded-tr-sm px-4 py-3 text-white text-sm leading-relaxed">
            {isEditing ? (
              <div className="space-y-2 min-w-[300px]">
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEditSubmit(); }
                    if (e.key === 'Escape') { setIsEditing(false); setEditContent(message.content); }
                  }}
                  className="w-full bg-[#1a1a1a] text-white rounded-lg px-3 py-2 text-sm outline-none border border-[#444] resize-none"
                  rows={Math.min(editContent.split('\n').length + 1, 10)}
                  autoFocus
                />
                <div className="flex gap-2 justify-end">
                  <button
                    onClick={() => { setIsEditing(false); setEditContent(message.content); }}
                    className="px-3 py-1 rounded-lg text-xs text-gray-400 hover:text-white border border-[#444] hover:border-[#666] transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleEditSubmit}
                    className="px-3 py-1 rounded-lg text-xs bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
                  >
                    Send
                  </button>
                </div>
              </div>
            ) : (
              message.content
            )}
          </div>
          <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1">
            <User size={14} className="text-white" />
          </div>
        </div>

        {/* User message actions */}
        {!isEditing && (
          <div className="flex justify-end mt-1 mr-10 gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => setIsEditing(true)}
              className="p-1 rounded hover:bg-[#2d2d2d] text-gray-500 hover:text-white transition-colors"
              title="Edit message"
            >
              <Pencil size={12} />
            </button>
          </div>
        )}
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex gap-4 mb-4 message-fade-in group">
      <div className="w-7 h-7 rounded-full bg-emerald-700 flex items-center justify-center flex-shrink-0 mt-1">
        <Bot size={14} className="text-white" />
      </div>

      <div className="flex-1 min-w-0">
        {/* Content */}
        <div
          className={cn(
            'prose-custom text-[#ececec] text-sm leading-relaxed',
            message.isStreaming && 'streaming-cursor'
          )}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{ code: CodeBlock } as any}
          >
            {message.content || (message.isStreaming ? '' : '_No response_')}
          </ReactMarkdown>
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setShowCitations(!showCitations)}
              className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              <BookOpen size={12} />
              {message.citations.length} source{message.citations.length > 1 ? 's' : ''}
              {showCitations ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showCitations && (
              <div className="mt-2 space-y-2">
                {message.citations.map((c) => (
                  <div key={c.citation_id} className="bg-[#1a1a1a] border border-[#333] rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-blue-400">📄 {c.filename}</span>
                      {c.page > 0 && <span className="text-xs text-gray-500">Page {c.page}</span>}
                      <span className="text-xs text-gray-600 ml-auto">Score: {(c.score * 100).toFixed(0)}%</span>
                    </div>
                    <p className="text-xs text-gray-400 line-clamp-3">{c.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Actions (not shown while streaming) */}
        {!message.isStreaming && (
          <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => copyToClipboard(message.content)}
              className="flex items-center gap-1 p-1.5 rounded-lg hover:bg-[#2d2d2d] text-gray-500 hover:text-white transition-colors"
              title="Copy"
            >
              {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
            </button>

            {isLast && (
              <button
                onClick={handleRegenerate}
                disabled={isStreaming}
                className="flex items-center gap-1 p-1.5 rounded-lg hover:bg-[#2d2d2d] text-gray-500 hover:text-white transition-colors disabled:opacity-50"
                title="Regenerate response"
              >
                <RotateCcw size={14} />
              </button>
            )}

            <div className="w-px h-4 bg-[#333] mx-1" />

            <button
              onClick={() => handleFeedback(1)}
              className={cn(
                'p-1.5 rounded-lg transition-colors',
                message.feedback === 1
                  ? 'text-emerald-400 bg-emerald-400/10'
                  : 'text-gray-500 hover:text-white hover:bg-[#2d2d2d]'
              )}
              title="Good response"
            >
              <ThumbsUp size={14} />
            </button>
            <button
              onClick={() => handleFeedback(-1)}
              className={cn(
                'p-1.5 rounded-lg transition-colors',
                message.feedback === -1
                  ? 'text-red-400 bg-red-400/10'
                  : 'text-gray-500 hover:text-white hover:bg-[#2d2d2d]'
              )}
              title="Bad response"
            >
              <ThumbsDown size={14} />
            </button>

            {message.model && (
              <span className="ml-2 text-xs text-gray-600">{message.model}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
