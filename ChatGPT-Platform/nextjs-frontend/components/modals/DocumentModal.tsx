'use client';

import { useState, useRef } from 'react';
import { X, Upload, Trash2, FileText, Loader2, CheckCircle } from 'lucide-react';
import { useStore } from '@/lib/store';
import * as api from '@/lib/api';
import { cn, formatFileSize, getFileIcon } from '@/lib/utils';

interface DocumentModalProps {
  onClose: () => void;
}

export function DocumentModal({ onClose }: DocumentModalProps) {
  const { documents, addDocument, removeDocument } = useStore();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ALLOWED = ['.pdf', '.docx', '.doc', '.txt', '.csv', '.json', '.md'];

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;

    const valid = Array.from(files).filter((f) => {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase();
      return ALLOWED.includes(ext);
    });

    if (valid.length === 0) {
      alert('Please select supported files: PDF, DOCX, TXT, CSV, JSON, MD');
      return;
    }

    setUploading(true);
    for (const file of valid) {
      setUploadProgress(`Uploading ${file.name}...`);
      try {
        const result = await api.uploadDocument(file);
        addDocument(result);
      } catch (err: any) {
        console.error(err.message);
      }
    }
    setUploading(false);
    setUploadProgress(null);
  }

  async function handleDelete(docId: string, filename: string) {
    if (!confirm(`Delete "${filename}"?`)) return;
    try {
      await api.deleteDocument(docId);
      removeDocument(docId);
    } catch { }
  }

  const totalChunks = documents.reduce((sum, d) => sum + d.chunk_count, 0);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#1a1a1a] border border-[#333] rounded-2xl w-full max-w-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#2d2d2d]">
          <div>
            <h2 className="text-lg font-semibold text-white">My Documents</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {documents.length} file{documents.length !== 1 ? 's' : ''} · {totalChunks} indexed chunks
            </p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[#2d2d2d] text-gray-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Drop zone */}
        <div className="p-6">
          <div
            className={cn(
              'border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer',
              isDragging ? 'border-emerald-500 bg-emerald-500/5' : 'border-[#333] hover:border-[#555]'
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
              <div className="flex flex-col items-center gap-3">
                <Loader2 size={32} className="text-emerald-400 animate-spin" />
                <p className="text-sm text-gray-400">{uploadProgress}</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-[#2d2d2d] flex items-center justify-center">
                  <Upload size={22} className="text-gray-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">Drop files or click to upload</p>
                  <p className="text-xs text-gray-500 mt-1">PDF, DOCX, TXT, CSV, JSON, MD · Max 50MB each</p>
                </div>
              </div>
            )}
          </div>

          {/* File list */}
          {documents.length > 0 ? (
            <div className="mt-4 space-y-2 max-h-64 overflow-y-auto">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 p-3 bg-[#212121] rounded-xl border border-[#2d2d2d] hover:border-[#444] transition-colors"
                >
                  <span className="text-xl">{getFileIcon(doc.file_type)}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{doc.filename}</p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(doc.file_size)} · {doc.chunk_count} chunks
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <CheckCircle size={14} className="text-emerald-400" />
                    <button
                      onClick={() => handleDelete(doc.id, doc.filename)}
                      className="p-1 rounded hover:bg-red-500/20 text-gray-500 hover:text-red-400 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-4 text-center text-sm text-gray-600 py-4">
              No documents uploaded yet. Upload files to enable document Q&A.
            </div>
          )}

          <p className="text-xs text-gray-600 text-center mt-4">
            💡 Enable "Doc Search" in the chat input to use your documents for Q&A
          </p>
        </div>
      </div>
    </div>
  );
}
