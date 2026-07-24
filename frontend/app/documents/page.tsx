"use client";

import { useState, useEffect, useCallback } from "react";
import { GlassCard, Button, StatusBadge, EmptyState } from "@/components/ui";
import { documentsApi } from "@/lib/api";
import { formatBytes, formatDate, getFileIcon } from "@/lib/utils";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const fetchDocs = useCallback(async () => {
    try {
      const data = await documentsApi.list({ page, page_size: 20, search: search || undefined });
      setDocuments(data.documents || []);
      setTotal(data.total || 0);
    } catch (e) {
      console.error("Failed to fetch documents:", e);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  // Poll for status updates when documents are in progress
  useEffect(() => {
    const hasInProgress = documents.some(
      (d: any) => d.status === "pending" || d.status === "processing" || d.status === "embedding"
    );
    if (!hasInProgress) return;
    const interval = setInterval(() => {
      fetchDocs();
    }, 3000);
    return () => clearInterval(interval);
  }, [documents, fetchDocs]);

  // ── File Upload ────────────────────────────────────────────

  const handleUpload = async (files: FileList | File[]) => {
    setUploading(true);
    const fileArray = Array.from(files);

    console.group(`📄 [Documents Page] Starting Upload for ${fileArray.length} file(s)`);
    console.log("Selected Files List:", fileArray.map((f) => ({
      name: f.name,
      size: (f.size / (1024 * 1024)).toFixed(2) + " MB",
      type: f.type || "unknown/extension"
    })));

    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i];
      console.log(`⏳ Uploading file ${i + 1}/${fileArray.length}: "${file.name}"...`);
      try {
        const res = await documentsApi.upload(file);
        console.log(`✅ Upload complete for "${file.name}":`, res);
      } catch (e: any) {
        console.error(`❌ Upload failed for "${file.name}":`, e);
        alert(`Upload failed for ${file.name}: ${e.message}`);
      }
    }

    console.log("🎉 All file upload tasks finished processing.");
    console.groupEnd();

    setUploading(false);
    fetchDocs();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files) handleUpload(e.dataTransfer.files);
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this document and its embeddings?")) return;
    try {
      await documentsApi.delete(id);
      // Optimistically remove from list immediately
      setDocuments((prev) => prev.filter((d: any) => d.id !== id));
      setTotal((prev) => Math.max(0, prev - 1));
    } catch (e: any) {
      console.error("Delete failed:", e);
      alert(`Delete failed: ${e.message}\n\nPlease check that the backend server is running on port 8080.`);
    }
    // Always refresh to get latest state
    fetchDocs();
  };

  const handleReprocess = async (id: string) => {
    try {
      await documentsApi.process(id);
      fetchDocs();
    } catch (e: any) {
      alert(`Reprocess failed: ${e.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Documents</h1>
          <p className="text-sm text-gray-400">{total} documents in your knowledge base</p>
        </div>
        <div>
          <input
            id="file-upload"
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.md,.txt,.html"
            className="hidden"
            onChange={(e) => e.target.files && handleUpload(e.target.files)}
          />
          <label
            htmlFor="file-upload"
            className={`inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-violet-500/25 transition-all duration-200 hover:from-violet-500 hover:to-indigo-500 hover:shadow-violet-500/40 ${uploading ? "pointer-events-none opacity-50" : ""}`}
          >
            {uploading ? "Uploading..." : "📤 Upload Files"}
          </label>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`rounded-2xl border-2 border-dashed p-8 text-center transition-all duration-300 ${
          dragActive
            ? "border-violet-500 bg-violet-500/5 shadow-lg shadow-violet-500/10"
            : "border-white/[0.08] bg-white/[0.02] hover:border-white/[0.15]"
        }`}
      >
        <p className="text-3xl">{dragActive ? "📥" : "📂"}</p>
        <p className="mt-2 text-sm font-medium text-gray-300">
          {dragActive ? "Drop files here" : "Drag & drop files here"}
        </p>
        <p className="mt-1 text-xs text-gray-500">
          Supports PDF, DOCX, Markdown, TXT, HTML • OCR for scanned PDFs
        </p>
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Search documents..."
        value={search}
        onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        className="w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:border-violet-500/50"
      />

      {/* Document List */}
      {documents.length === 0 && !loading ? (
        <EmptyState
          icon="📭"
          title="No documents yet"
          description="Upload your first document to start building your knowledge base. PDFs, DOCX, Markdown, and more are supported."
        />
      ) : (
        <div className="space-y-3">
          {documents.map((doc: any) => (
            <GlassCard key={doc.id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/[0.04] text-2xl">
                    {getFileIcon(doc.file_type)}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">{doc.title}</h3>
                    <div className="mt-1 flex items-center gap-3 text-[10px] text-gray-500">
                      <span>{doc.file_type?.toUpperCase()}</span>
                      {doc.file_size && <span>{formatBytes(doc.file_size)}</span>}
                      {doc.page_count && <span>{doc.page_count} pages</span>}
                      <span>{doc.chunk_count} chunks</span>
                      {doc.ocr_applied && (
                        <span className="rounded bg-purple-500/10 px-1.5 py-0.5 text-purple-400">OCR</span>
                      )}
                      {doc.has_tables && (
                        <span className="rounded bg-blue-500/10 px-1.5 py-0.5 text-blue-400">Tables</span>
                      )}
                    </div>
                    {doc.summary && (
                      <p className="mt-1 max-w-xl text-xs text-gray-400 line-clamp-1">{doc.summary}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <StatusBadge status={doc.status} />
                  <div className="flex gap-1">
                    {doc.status === "failed" && (
                      <Button variant="ghost" size="sm" onClick={() => handleReprocess(doc.id)}>🔄</Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(doc.id)}>🗑️</Button>
                  </div>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2">
          <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            ← Previous
          </Button>
          <span className="px-3 py-1.5 text-xs text-gray-400">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <Button variant="ghost" size="sm" disabled={page >= Math.ceil(total / 20)} onClick={() => setPage(page + 1)}>
            Next →
          </Button>
        </div>
      )}
    </div>
  );
}
