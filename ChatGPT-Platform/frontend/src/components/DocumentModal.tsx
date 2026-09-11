import React, { useState, useRef } from 'react';
import { X, UploadCloud, FileText, Trash2, CheckCircle2, AlertCircle, Sparkles, Loader2 } from 'lucide-react';
import { DocumentItem } from '../types';
import { uploadDocument, deleteDocument, deleteAllDocuments } from '../api';

interface DocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  documents: DocumentItem[];
  onDocumentsUpdated: () => void;
  useRag: boolean;
  setUseRag: (val: boolean) => void;
}

export const DocumentModal: React.FC<DocumentModalProps> = ({
  isOpen,
  onClose,
  documents,
  onDocumentsUpdated,
  useRag,
  setUseRag,
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [isClearingAll, setIsClearingAll] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setErrorMsg(null);
    setUploadStatus('Uploading & chunking document for vector search...');

    try {
      for (let i = 0; i < files.length; i++) {
        await uploadDocument(files[i]);
      }
      setUploadStatus('Documents indexed successfully into RAG memory!');
      onDocumentsUpdated();
      setTimeout(() => setUploadStatus(null), 3500);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to upload document.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    setErrorMsg(null);
    try {
      await deleteDocument(id);
      onDocumentsUpdated();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete document.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to delete ALL uploaded documents? This will completely clear the RAG knowledge base.')) {
      return;
    }
    setIsClearingAll(true);
    setErrorMsg(null);
    try {
      await deleteAllDocuments();
      onDocumentsUpdated();
      setUploadStatus('All documents removed and RAG knowledge base reset.');
      setTimeout(() => setUploadStatus(null), 3500);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to clear all documents.');
    } finally {
      setIsClearingAll(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-[#0f172a]/95 border border-white/[0.12] rounded-3xl w-full max-w-2xl overflow-hidden shadow-[0_25px_60px_-15px_rgba(0,0,0,0.7)] flex flex-col max-h-[85vh] backdrop-blur-2xl">
        {/* Accent top border */}
        <div className="h-1 w-full bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-500" />

        {/* Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white tracking-tight">Document Knowledge Base (RAG)</h3>
              <p className="text-[11px] text-gray-400">Upload documents or delete them anytime to control what AI references</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-gray-400 hover:text-white hover:bg-white/[0.08] transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          {/* RAG Toggle */}
          <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-7 h-7 rounded-xl bg-emerald-500/15 flex items-center justify-center text-emerald-400">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="text-xs font-semibold text-white">Enable RAG Grounding</div>
                <div className="text-[11px] text-gray-400">Augment answers with relevant excerpts from your active documents</div>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={useRag}
                onChange={(e) => setUseRag(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-10 h-5 bg-white/[0.1] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-emerald-500 peer-checked:to-teal-500" />
            </label>
          </div>

          {/* Upload Dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-white/[0.12] hover:border-emerald-500/60 bg-white/[0.02] hover:bg-emerald-500/[0.02] rounded-2xl p-6 text-center cursor-pointer transition-all group"
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.txt,.csv,.json,.md"
              onChange={(e) => handleFileUpload(e.target.files)}
              className="hidden"
            />
            <UploadCloud className="w-10 h-10 text-gray-400 group-hover:text-emerald-400 group-hover:scale-110 transition-all mx-auto mb-2" />
            <p className="text-xs font-semibold text-white">Click or drag & drop files to upload</p>
            <p className="text-[11px] text-gray-400 mt-1">Supports PDF, DOCX, TXT, CSV, JSON, Markdown (up to 50MB)</p>
          </div>

          {/* Upload / Status Feedback */}
          {uploadStatus && (
            <div className="p-3 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-xs text-emerald-300 flex items-center space-x-2.5">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{uploadStatus}</span>
            </div>
          )}

          {errorMsg && (
            <div className="p-3 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-xs text-rose-300 flex items-center space-x-2.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Uploaded Documents List */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Indexed Documents ({documents.length})
              </span>

              {documents.length > 0 && (
                <button
                  onClick={handleClearAll}
                  disabled={isClearingAll}
                  className="text-xs text-rose-400 hover:text-rose-300 hover:underline flex items-center space-x-1 transition-colors"
                >
                  {isClearingAll ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                  <span>Delete All Documents</span>
                </button>
              )}
            </div>

            {documents.length === 0 ? (
              <div className="p-6 text-center text-xs text-gray-400 bg-white/[0.02] rounded-2xl border border-white/[0.06]">
                No documents uploaded yet. Upload a PDF or text document above to ground chat responses in your files.
              </div>
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-3 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-between text-xs hover:border-emerald-500/30 transition-all"
                  >
                    <div className="flex items-center space-x-3 truncate pr-2">
                      <div className="w-8 h-8 rounded-xl bg-emerald-500/15 text-emerald-300 flex items-center justify-center font-mono text-[10px] font-bold uppercase shrink-0 border border-emerald-500/20">
                        {doc.file_type}
                      </div>
                      <div className="truncate">
                        <div className="font-medium text-white truncate">{doc.filename}</div>
                        <div className="text-[10px] text-gray-400">
                          {formatBytes(doc.file_size)} • {doc.chunk_count} chunks indexed
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDelete(doc.id)}
                      disabled={deletingId === doc.id}
                      title="Delete document and remove from RAG memory"
                      className="p-2 text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition-all shrink-0"
                    >
                      {deletingId === doc.id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/[0.08] bg-black/20 flex items-center justify-between">
          <span className="text-[11px] text-gray-400">
            {documents.length > 0 ? `${documents.length} file(s) available for RAG` : 'RAG index is empty'}
          </span>
          <button
            onClick={onClose}
            className="px-5 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white text-xs font-semibold rounded-xl shadow-md shadow-emerald-500/20 transition-all active:scale-[0.98]"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
