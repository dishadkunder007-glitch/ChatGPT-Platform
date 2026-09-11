'use client';

import { useRef, useState, useCallback } from 'react';
import { Send, Square, Paperclip, X, ToggleLeft, ToggleRight, Loader2 } from 'lucide-react';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import { getFileIcon, formatFileSize } from '@/lib/utils';
import * as api from '@/lib/api';

interface InputBoxProps {
  onSend: (message: string, files?: File[]) => void;
  onStop: () => void;
}

export function InputBox({ onSend, onStop }: InputBoxProps) {
  const { isStreaming, useRag, setUseRag, setDocuments, documents } = useStore();
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ALLOWED_TYPES = ['.pdf', '.docx', '.doc', '.txt', '.csv', '.json', '.md'];

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    // Auto-resize
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  async function handleSend() {
    if ((!input.trim() && files.length === 0) || isStreaming) return;

    const msg = input.trim();
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    // Upload pending files first
    if (files.length > 0) {
      setUploading(true);
      for (const file of files) {
        try {
          const result = await api.uploadDocument(file);
          useStore.getState().addDocument(result);
        } catch (err: any) {
          console.error('Upload failed:', err.message);
        }
      }
      setFiles([]);
      setUploading(false);
    }

    onSend(msg || `I've uploaded ${files.length} document(s). Please confirm.`);
  }

  function handleFileSelect(selected: FileList | null) {
    if (!selected) return;
    const valid = Array.from(selected).filter((f) => {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase();
      return ALLOWED_TYPES.includes(ext);
    });
    setFiles((prev) => [...prev, ...valid]);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  }

  return (
    <div className="border-t border-[#2d2d2d] bg-[#0f0f0f] px-4 py-3">
      {/* Active Knowledge / Documents Pill */}
      {documents.length > 0 && (
        <div className="flex items-center justify-between mb-2.5 px-2 py-1.5 bg-zinc-900/80 border border-zinc-800 rounded-xl text-xs text-zinc-400">
          <div className="flex items-center gap-2 overflow-hidden">
            <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0 animate-pulse" />
            <span className="font-medium text-zinc-200 flex-shrink-0">
              Active Documents ({documents.length}):
            </span>
            <span className="text-zinc-400 truncate max-w-[280px] sm:max-w-[450px]">
              {documents.map((d) => d.filename).join(', ')}
            </span>
          </div>
          <button
            onClick={() => useStore.getState().setDocModalOpen(true)}
            className="text-emerald-400 hover:text-emerald-300 text-xs font-medium hover:underline flex-shrink-0 ml-3"
          >
            Manage / Delete
          </button>
        </div>
      )}
      {/* File previews */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {files.map((file, idx) => (
            <div key={idx} className="flex items-center gap-2 bg-[#1a1a1a] border border-[#333] rounded-lg px-3 py-1.5 text-xs">
              <span>{getFileIcon(file.name.split('.').pop() || '')}</span>
              <span className="text-gray-300 max-w-[120px] truncate">{file.name}</span>
              <span className="text-gray-500">{formatFileSize(file.size)}</span>
              <button
                onClick={() => setFiles((prev) => prev.filter((_, i) => i !== idx))}
                className="text-gray-500 hover:text-red-400 ml-1"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Main input area */}
      <div
        className={cn(
          'relative flex flex-col bg-[#1a1a1a] border rounded-2xl transition-all input-glow',
          isDragging ? 'border-emerald-500 bg-emerald-500/5' : 'border-[#333]'
        )}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={isDragging ? 'Drop files here...' : 'Message ChatGPT Platform...'}
          disabled={isStreaming && !uploading}
          rows={1}
          className="w-full bg-transparent text-white placeholder-gray-500 text-sm px-4 pt-4 pb-2 outline-none resize-none min-h-[52px] max-h-[200px] leading-relaxed"
        />

        {/* Bottom toolbar */}
        <div className="flex items-center justify-between px-3 pb-3 pt-1">
          <div className="flex items-center gap-2">
            {/* File attach button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#2d2d2d] transition-colors"
              title="Attach file (PDF, DOCX, TXT, CSV, JSON)"
            >
              <Paperclip size={16} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ALLOWED_TYPES.join(',')}
              className="hidden"
              onChange={(e) => handleFileSelect(e.target.files)}
            />

            {/* RAG toggle */}
            <button
              onClick={() => setUseRag(!useRag)}
              className={cn(
                'flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg transition-colors',
                useRag
                  ? 'text-emerald-400 bg-emerald-400/10 hover:bg-emerald-400/20'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-[#2d2d2d]'
              )}
              title={useRag ? 'Document search ON' : 'Document search OFF'}
            >
              {useRag ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
              <span className="hidden sm:inline">Doc Search</span>
            </button>

            {/* Uploading indicator */}
            {uploading && (
              <div className="flex items-center gap-1.5 text-xs text-yellow-400">
                <Loader2 size={12} className="animate-spin" />
                Uploading...
              </div>
            )}
          </div>

          {/* Send / Stop button */}
          <div className="flex items-center gap-2">
            {input.trim() && (
              <span className="text-xs text-gray-600">
                {input.length > 200 ? `${input.length} chars` : ''}
              </span>
            )}
            {isStreaming ? (
              <button
                onClick={onStop}
                className="flex items-center justify-center w-8 h-8 rounded-lg bg-white text-black hover:bg-gray-200 transition-colors"
                title="Stop generating"
              >
                <Square size={14} />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!input.trim() && files.length === 0}
                className={cn(
                  'flex items-center justify-center w-8 h-8 rounded-lg transition-all',
                  (input.trim() || files.length > 0)
                    ? 'bg-white text-black hover:bg-gray-200 scale-100'
                    : 'bg-[#333] text-gray-600 cursor-not-allowed scale-95'
                )}
              >
                <Send size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

      <p className="text-center text-xs text-gray-600 mt-2">
        ChatGPT Platform may produce inaccurate information. Drag & drop files to upload.
      </p>
    </div>
  );
}
