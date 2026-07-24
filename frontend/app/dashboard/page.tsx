"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { StatsCard, GlassCard, StatusBadge, Button } from "@/components/ui";
import { documentsApi, adminApi, obsidianApi, chatApi } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState({
    documents: 0,
    conversations: 0,
    models: 0,
    syncStatus: "disconnected",
  });
  const [recentDocs, setRecentDocs] = useState<any[]>([]);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [docs, conversations, models, system] = await Promise.allSettled([
          documentsApi.list({ page_size: 5 }),
          chatApi.history(),
          adminApi.models(),
          adminApi.system(),
        ]);

        if (docs.status === "fulfilled") {
          setRecentDocs(docs.value.documents || []);
          setStats((s) => ({ ...s, documents: docs.value.total || 0 }));
        }
        if (conversations.status === "fulfilled") {
          setStats((s) => ({ ...s, conversations: conversations.value.length || 0 }));
        }
        if (models.status === "fulfilled") {
          setStats((s) => ({ ...s, models: models.value.length || 0 }));
        }
        if (system.status === "fulfilled") {
          setSystemHealth(system.value);
        }
      } catch (e) {
        console.error("Dashboard load error:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">
          Welcome to <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">ARIA</span>
        </h1>
        <p className="mt-1 text-gray-400">Your AI Research & Intelligence Assistant</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard
          title="Documents"
          value={stats.documents}
          subtitle="In knowledge base"
          icon="📁"
          gradient="bg-violet-500"
        />
        <StatsCard
          title="Conversations"
          value={stats.conversations}
          subtitle="RAG chat sessions"
          icon="💬"
          gradient="bg-indigo-500"
        />
        <StatsCard
          title="AI Models"
          value={stats.models}
          subtitle="Available in Ollama"
          icon="🤖"
          gradient="bg-cyan-500"
        />
        <StatsCard
          title="System Status"
          value={systemHealth?.status === "healthy" ? "Online" : "Check"}
          subtitle={systemHealth?.ollama?.chat_model || "Connecting..."}
          icon="⚡"
          gradient="bg-emerald-500"
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Quick Actions Card */}
        <GlassCard className="p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Quick Actions</h2>
          <div className="mt-4 flex flex-col gap-3">
            <Link href="/chat">
              <Button variant="primary" size="lg" className="w-full">💬 Start a Chat</Button>
            </Link>
            <Link href="/documents">
              <Button variant="secondary" size="lg" className="w-full">📤 Upload Document</Button>
            </Link>
            <Link href="/reports">
              <Button variant="secondary" size="lg" className="w-full">📋 Generate Report</Button>
            </Link>
            <Link href="/news">
              <Button variant="ghost" size="lg" className="w-full">📰 Browse Papers</Button>
            </Link>
          </div>
        </GlassCard>

        {/* Recent Documents */}
        <GlassCard className="col-span-1 p-6 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Recent Documents</h2>
            <Link href="/documents" className="text-xs text-violet-400 hover:text-violet-300">View all →</Link>
          </div>
          <div className="mt-4 space-y-3">
            {recentDocs.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-3xl">📭</p>
                <p className="mt-2 text-sm text-gray-500">No documents yet. Upload your first file!</p>
              </div>
            ) : (
              recentDocs.map((doc: any) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between rounded-xl border border-white/[0.04] bg-white/[0.02] px-4 py-3 transition-colors hover:bg-white/[0.04]"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">
                      {doc.file_type === "pdf" ? "📄" : doc.file_type === "md" ? "📋" : "📝"}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-white">{doc.title}</p>
                      <p className="text-[10px] text-gray-500">
                        {doc.file_type?.toUpperCase()} • {doc.chunk_count} chunks
                        {doc.ocr_applied && " • OCR"}
                      </p>
                    </div>
                  </div>
                  <StatusBadge status={doc.status} />
                </div>
              ))
            )}
          </div>
        </GlassCard>
      </div>

      {/* System Health */}
      {systemHealth && (
        <GlassCard className="p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">System Health</h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-white/[0.04] bg-white/[0.02] p-4">
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${systemHealth.ollama?.status === "healthy" ? "bg-emerald-400" : "bg-red-400"}`} />
                <span className="text-sm font-medium text-white">Ollama</span>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                {systemHealth.ollama?.models_available || 0} models available
              </p>
            </div>
            <div className="rounded-xl border border-white/[0.04] bg-white/[0.02] p-4">
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${systemHealth.chromadb?.total_chunks !== undefined ? "bg-emerald-400" : "bg-red-400"}`} />
                <span className="text-sm font-medium text-white">ChromaDB</span>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                {systemHealth.chromadb?.total_chunks || 0} chunks stored
              </p>
            </div>
            <div className="rounded-xl border border-white/[0.04] bg-white/[0.02] p-4">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-emerald-400" />
                <span className="text-sm font-medium text-white">PostgreSQL</span>
              </div>
              <p className="mt-1 text-xs text-gray-500">Connected</p>
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
