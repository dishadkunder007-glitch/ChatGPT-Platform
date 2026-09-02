import React, { useState, useRef } from 'react';
import { X, UploadCloud, FileText, Trash2, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import { DocumentItem } from '../types';
import { uploadDocument, deleteDocument } from '../api';

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
      setUploadStatus('Document indexed successfully!');
      onDocumentsUpdated();
      setTimeout(() => setUploadStatus(null), 3000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to upload document.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      onDocumentsUpdated();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete document.');
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
      <div className="bg-[#191e27] border border-[#2b3342] rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#282f3c] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#10a37f]/20 flex items-center justify-center text-[#10a37f]">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">Document Manager (RAG)</h3>
              <p className="text-xs text-[#8e8ea0]">Upload files to ground LLM responses with source citations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#8e8ea0] hover:text-white hover:bg-[#252c39] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          {/* RAG Toggle */}
          <div className="p-3.5 rounded-xl bg-[#141820] border border-[#283244] flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <Sparkles className="w-4 h-4 text-[#10a37f]" />
              <div>
                <div className="text-xs font-semibold text-white">Enable RAG Grounding</div>
                <div className="text-[11px] text-[#8e8ea0]">Automatically augment chat with relevant document chunks</div>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={useRag}
                onChange={(e) => setUseRag(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-10 h-5 bg-[#2b3342] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#10a37f]" />
            </label>
          </div>

          {/* Upload Dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-[#2f384a] hover:border-[#10a37f]/60 bg-[#141820]/60 rounded-xl p-6 text-center cursor-pointer transition-all hover:bg-[#141820] group"
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.txt,.csv,.json,.md"
              onChange={(e) => handleFileUpload(e.target.files)}
              className="hidden"
            />
            <UploadCloud className="w-10 h-10 text-[#8e8ea0] group-hover:text-[#10a37f] group-hover:scale-110 transition-all mx-auto mb-2" />
            <p className="text-xs font-semibold text-white">Click or drag & drop files to upload</p>
            <p className="text-[11px] text-[#6e7681] mt-1">Supports PDF, DOCX, TXT, CSV, JSON, Markdown (up to 25MB)</p>
          </div>

          {/* Upload Feedback */}
          {uploadStatus && (
            <div className="p-3 rounded-lg bg-[#10a37f]/15 border border-[#10a37f]/40 text-xs text-[#10a37f] flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{uploadStatus}</span>
            </div>
          )}

          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/15 border border-rose-500/40 text-xs text-rose-400 flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Uploaded Documents List */}
          <div>
            <div className="text-xs font-semibold text-[#8e8ea0] uppercase tracking-wider mb-2">
              Indexed Documents ({documents.length})
            </div>

            {documents.length === 0 ? (
              <div className="p-6 text-center text-xs text-[#6e7681] bg-[#141820] rounded-xl border border-[#232a38]">
                No documents uploaded yet. Upload PDFs or documents to ask questions grounded in your data!
              </div>
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-3 rounded-xl bg-[#141820] border border-[#262e3d] flex items-center justify-between text-xs hover:border-[#354054] transition-colors"
                  >
                    <div className="flex items-center space-x-3 truncate pr-2">
                      <div className="w-7 h-7 rounded-lg bg-[#10a37f]/15 text-[#10a37f] flex items-center justify-center font-mono text-[10px] font-bold uppercase shrink-0">
                        {doc.file_type}
                      </div>
                      <div className="truncate">
                        <div className="font-medium text-white truncate">{doc.filename}</div>
                        <div className="text-[10px] text-[#6e7681]">
                          {formatBytes(doc.file_size)} • {doc.chunk_count} chunks indexed
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDelete(doc.id)}
                      title="Delete document"
                      className="p-1.5 text-[#6e7681] hover:text-rose-400 hover:bg-[#252c39] rounded-lg transition-colors shrink-0"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-[#282f3c] bg-[#141820] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#10a37f] hover:bg-[#0e8e6e] text-white text-xs font-semibold rounded-lg transition-all"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
