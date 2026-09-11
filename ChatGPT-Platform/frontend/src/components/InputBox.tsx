import React, { useRef, useEffect, useState } from 'react';
import { Paperclip, Square, ArrowUp, Sparkles, FileText, Trash2, X, Plus, UploadCloud, Loader2 } from 'lucide-react';
import { DocumentItem } from '../types';

interface InputBoxProps {
  input: string;
  setInput: (val: string) => void;
  onSend: () => void;
  onStop: () => void;
  isStreaming: boolean;
  onOpenDocumentManager: () => void;
  attachedDocsCount: number;
  useRag: boolean;
  documents?: DocumentItem[];
  onDeleteDocument?: (docId: string) => Promise<void>;
  onUploadFile?: (file: File) => Promise<void>;
  onClearAllDocuments?: () => Promise<void>;
}

export const InputBox: React.FC<InputBoxProps> = ({
  input,
  setInput,
  onSend,
  onStop,
  isStreaming,
  onOpenDocumentManager,
  attachedDocsCount,
  useRag,
  documents = [],
  onDeleteDocument,
  onUploadFile,
  onClearAllDocuments,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isStreaming) {
        onSend();
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !onUploadFile) return;

    setIsUploading(true);
    try {
      for (let i = 0; i < files.length; i++) {
        await onUploadFile(files[i]);
      }
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (!onUploadFile || !e.dataTransfer.files?.length) return;

    setIsUploading(true);
    try {
      for (let i = 0; i < e.dataTransfer.files.length; i++) {
        await onUploadFile(e.dataTransfer.files[i]);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onDeleteDocument) return;
    setDeletingId(docId);
    try {
      await onDeleteDocument(docId);
    } finally {
      setDeletingId(null);
    }
  };

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div
      className="w-full max-w-4xl mx-auto px-4 pb-4 select-none"
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.doc,.txt,.csv,.json,.md"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Uploaded Documents Strip */}
      {documents.length > 0 && (
        <div className="mb-2 px-1 flex items-center justify-between animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="flex items-center space-x-1.5 overflow-x-auto py-1 max-w-[80%] scrollbar-none">
            <span className="text-[11px] font-semibold text-emerald-400/90 flex items-center shrink-0 mr-1">
              <FileText className="w-3.5 h-3.5 mr-1" />
              Active Context:
            </span>

            {documents.map((doc) => (
              <div
                key={doc.id}
                className="group relative flex items-center space-x-1.5 px-2.5 py-1 rounded-xl bg-[#0f172a]/90 border border-emerald-500/30 hover:border-emerald-400/60 shadow-sm text-xs text-gray-200 shrink-0 transition-all backdrop-blur-md"
                title={`${doc.filename} (${formatBytes(doc.file_size)}, ${doc.chunk_count} chunks)`}
              >
                <span className="text-[9px] font-bold uppercase px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono">
                  {doc.file_type}
                </span>
                <span className="max-w-[120px] truncate text-[11px] font-medium text-gray-200">
                  {doc.filename}
                </span>

                {/* Direct Delete Document Button */}
                <button
                  onClick={(e) => handleDelete(doc.id, e)}
                  disabled={deletingId === doc.id}
                  title="Remove document from RAG memory"
                  className="p-0.5 rounded-full text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors ml-0.5"
                >
                  {deletingId === doc.id ? (
                    <Loader2 className="w-3 h-3 animate-spin text-rose-400" />
                  ) : (
                    <X className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            ))}

            {/* Quick Add Document Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              title="Upload another document"
              className="flex items-center space-x-1 px-2 py-1 rounded-xl bg-white/[0.04] border border-white/[0.08] hover:border-white/20 hover:bg-white/[0.08] text-[11px] text-gray-400 hover:text-white shrink-0 transition-all"
            >
              {isUploading ? (
                <Loader2 className="w-3 h-3 animate-spin text-emerald-400" />
              ) : (
                <Plus className="w-3 h-3" />
              )}
              <span>Add</span>
            </button>
          </div>

          {/* Clear All Documents Button */}
          {onClearAllDocuments && (
            <button
              onClick={onClearAllDocuments}
              className="text-[11px] text-gray-400 hover:text-rose-400 hover:underline flex items-center space-x-1 transition-colors shrink-0 ml-2"
              title="Delete all uploaded documents and clear RAG index"
            >
              <Trash2 className="w-3 h-3" />
              <span>Clear All</span>
            </button>
          )}
        </div>
      )}

      {/* Floating curved container with glassmorphic glow */}
      <div
        className={`relative rounded-3xl bg-[#0f172a]/90 backdrop-blur-2xl border ${
          isDragging
            ? 'border-emerald-400 ring-2 ring-emerald-400/30 bg-emerald-950/20'
            : 'border-white/[0.12] focus-within:border-emerald-500/80 focus-within:ring-2 focus-within:ring-emerald-500/20'
        } shadow-2xl transition-all flex items-end p-2 sm:p-2.5`}
      >
        {/* Paperclip / File Upload Button */}
        <div className="relative flex items-center">
          <button
            onClick={() => fileInputRef.current?.click()}
            title="Upload document (PDF, TXT, DOCX, CSV) or click to manage"
            className="relative p-2.5 text-gray-400 hover:text-white hover:bg-white/[0.08] rounded-2xl transition-all shrink-0 group"
          >
            {isUploading ? (
              <Loader2 className="w-5 h-5 animate-spin text-emerald-400" />
            ) : (
              <Paperclip className="w-5 h-5 -rotate-45 group-hover:scale-110 transition-transform text-gray-400 group-hover:text-emerald-400" />
            )}
            {attachedDocsCount > 0 && !isUploading && (
              <span className="absolute top-1 right-1 px-1.5 py-0.2 rounded-full text-[9px] font-bold bg-emerald-500 text-black shadow-sm">
                {attachedDocsCount}
              </span>
            )}
          </button>

          {/* Manage Modal Trigger */}
          <button
            onClick={onOpenDocumentManager}
            title="Open Document Manager & RAG settings"
            className="hidden sm:inline-flex p-1.5 text-[10px] text-gray-400 hover:text-emerald-400 hover:bg-white/[0.05] rounded-xl transition-all mr-1"
          >
            Files
          </button>
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            documents.length > 0
              ? `Ask about your ${documents.length} document${documents.length > 1 ? 's' : ''}, or ask general questions...`
              : "Ask anything (e.g. 'Hi, how are you!!', write code, or attach documents to analyze)..."
          }
          rows={1}
          className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-500 px-3 py-2.5 focus:outline-none resize-none max-h-48 overflow-y-auto leading-relaxed"
        />

        {/* Action Button: Stop or Send */}
        <div className="shrink-0 pl-1.5 pb-0.5">
          {isStreaming ? (
            <button
              onClick={onStop}
              title="Stop generating"
              className="w-9 h-9 rounded-2xl bg-gradient-to-r from-rose-500 to-red-600 hover:from-rose-400 hover:to-red-500 text-white flex items-center justify-center transition-all shadow-lg shadow-rose-500/30 active:scale-95 animate-pulse"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
            </button>
          ) : (
            <button
              onClick={onSend}
              disabled={!input.trim()}
              title="Send message"
              className={`w-9 h-9 rounded-2xl flex items-center justify-center transition-all shadow-lg ${
                input.trim()
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white shadow-emerald-500/25 active:scale-95'
                  : 'bg-white/[0.05] text-gray-500 cursor-not-allowed border border-white/[0.05]'
              }`}
            >
              <ArrowUp className="w-4 h-4 stroke-[3]" />
            </button>
          )}
        </div>
      </div>

      {/* Footer information */}
      <div className="flex items-center justify-center space-x-2 mt-2 text-[11px] text-gray-400 text-center">
        <span>ChatGPT Platform</span>
        <span>•</span>
        <span className="flex items-center text-emerald-400/90 font-medium">
          <Sparkles className="w-3 h-3 mr-1" />
          {documents.length > 0 ? `${documents.length} Document${documents.length > 1 ? 's' : ''} Grounded` : 'Local AI Engine'}
        </span>
        <span>•</span>
        <span>{documents.length > 0 ? 'Upload or delete documents anytime' : 'Attach PDF/Docs for instant RAG analysis'}</span>
      </div>
    </div>
  );
};
