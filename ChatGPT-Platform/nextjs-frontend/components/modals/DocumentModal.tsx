'use client';

import { useState, useRef, useEffect } from 'react';
import { X, Upload, Trash2, FileText, Loader2, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import { useStore } from '@/lib/store';
import * as api from '@/lib/api';
import { cn, formatFileSize, getFileIcon } from '@/lib/utils';

interface DocumentModalProps {
  onClose: () => void;
}

export function DocumentModal({ onClose }: DocumentModalProps) {
  const { documents, setDocuments, addDocument, removeDocument, clearDocuments } = useStore();
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deletingAll, setDeletingAll] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ALLOWED = ['.pdf', '.docx', '.doc', '.txt', '.csv', '.json', '.md'];

  // Load existing documents from backend on modal mount
  useEffect(() => {
    let mounted = true;
    async function loadDocs() {
      setLoading(true);
      try {
        const docs = await api.getDocuments();
        if (mounted) {
          setDocuments(docs || []);
        }
      } catch (err: any) {
        console.error('Failed to load documents:', err);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadDocs();
    return () => {
      mounted = false;
    };
  }, [setDocuments]);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setErrorMsg(null);

    const valid = Array.from(files).filter((f) => {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase();
      return ALLOWED.includes(ext);
    });

    if (valid.length === 0) {
      setErrorMsg('Please select supported files: PDF, DOCX, TXT, CSV, JSON, or MD');
      return;
    }

    setUploading(true);
    for (const file of valid) {
      setUploadProgress(`Analyzing & indexing ${file.name}...`);
      try {
        const result = await api.uploadDocument(file);
        addDocument(result);
      } catch (err: any) {
        console.error(err);
        setErrorMsg(err.message || `Failed to upload ${file.name}`);
      }
    }
    setUploading(false);
    setUploadProgress(null);
  }

  async function handleDelete(docId: string, filename: string) {
    if (!confirm(`Are you sure you want to delete "${filename}"? This will remove all indexed chunks from RAG.`)) return;
    setDeletingId(docId);
    setErrorMsg(null);
    try {
      await api.deleteDocument(docId);
      removeDocument(docId);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  }

  async function handleDeleteAll() {
    if (!confirm(`Are you sure you want to delete ALL ${documents.length} document(s)? This will completely wipe RAG indexed memory.`)) return;
    setDeletingAll(true);
    setErrorMsg(null);
    try {
      await api.deleteAllDocuments();
      clearDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to clear documents');
    } finally {
      setDeletingAll(false);
    }
  }

  const totalChunks = documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0);

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="bg-[#18181b] border border-[#27272a] rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#27272a]">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <FileText size={18} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                Knowledge Base & Documents
                <span className="text-xs font-normal text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                  RAG Active
                </span>
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                {documents.length} file{documents.length !== 1 ? 's' : ''} uploaded · {totalChunks} indexed chunks
              </p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Error notice */}
        {errorMsg && (
          <div className="mx-6 mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-2.5 text-xs text-red-400">
            <AlertCircle size={15} className="flex-shrink-0" />
            <span className="flex-1">{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="text-red-400 hover:text-red-300">
              <X size={14} />
            </button>
          </div>
        )}

        {/* Drop zone */}
        <div className="p-6 overflow-y-auto space-y-4">
          <div
            className={cn(
              'border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer select-none',
              isDragging ? 'border-emerald-500 bg-emerald-500/5 shadow-inner' : 'border-zinc-700/70 hover:border-zinc-500 hover:bg-zinc-800/20'
            )}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ALLOWED.join(',')}
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />

            {uploading ? (
              <div className="flex flex-col items-center gap-3 py-2">
                <Loader2 size={32} className="text-emerald-400 animate-spin" />
                <p className="text-sm font-medium text-zinc-200">{uploadProgress}</p>
                <p className="text-xs text-zinc-500">Extracting text & computing vector embeddings...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2.5 py-1">
                <div className="w-11 h-11 rounded-xl bg-zinc-800 border border-zinc-700/60 flex items-center justify-center text-zinc-300 shadow-sm">
                  <Upload size={20} />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-200">
                    Drop files here, or <span className="text-emerald-400 underline decoration-emerald-500/30 underline-offset-2">browse</span>
                  </p>
                  <p className="text-xs text-zinc-500 mt-1">PDF, DOCX, TXT, CSV, JSON, MD · Up to 50MB</p>
                </div>
              </div>
            )}
          </div>

          {/* Document list header & action */}
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Uploaded Documents ({documents.length})
            </span>
            {documents.length > 0 && (
              <button
                onClick={handleDeleteAll}
                disabled={deletingAll}
                className="text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {deletingAll ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                Delete All
              </button>
            )}
          </div>

          {/* File list */}
          {loading ? (
            <div className="flex items-center justify-center py-8 text-zinc-500 gap-2 text-sm">
              <Loader2 size={16} className="animate-spin text-emerald-400" />
              Loading documents...
            </div>
          ) : documents.length > 0 ? (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {documents.map((doc) => {
                const isDeleting = deletingId === doc.id;
                return (
                  <div
                    key={doc.id}
                    className="flex items-center gap-3 p-3 bg-zinc-900/90 rounded-xl border border-zinc-800 hover:border-zinc-700 transition-colors group"
                  >
                    <span className="text-xl flex-shrink-0">{getFileIcon(doc.file_type)}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-zinc-200 truncate">{doc.filename}</p>
                      <div className="flex items-center gap-2 text-xs text-zinc-500 mt-0.5">
                        <span>{formatFileSize(doc.file_size)}</span>
                        <span>•</span>
                        <span className="text-emerald-400/90">{doc.chunk_count} chunks indexed</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <span className="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <CheckCircle2 size={11} /> Ready
                      </span>
                      <button
                        onClick={() => handleDelete(doc.id, doc.filename)}
                        disabled={isDeleting || deletingAll}
                        title="Delete document and remove from RAG"
                        className="p-1.5 rounded-lg hover:bg-red-500/20 text-zinc-400 hover:text-red-400 transition-colors disabled:opacity-50"
                      >
                        {isDeleting ? (
                          <Loader2 size={14} className="animate-spin text-red-400" />
                        ) : (
                          <Trash2 size={14} />
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-8 text-center rounded-xl bg-zinc-900/40 border border-zinc-800/80 text-zinc-500 text-xs">
              <FileText size={28} className="mx-auto mb-2 text-zinc-600 opacity-60" />
              No documents currently uploaded.
              <p className="mt-1 text-zinc-600">Upload documents above to analyze and chat with your content.</p>
            </div>
          )}

          {/* Footer note */}
          <div className="pt-2 border-t border-zinc-800/80 flex items-center justify-between text-xs text-zinc-500">
            <span className="flex items-center gap-1.5">
              <Sparkles size={12} className="text-emerald-400" />
              RAG answers queries directly from your uploaded files
            </span>
            <button
              onClick={onClose}
              className="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-xs font-medium transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
