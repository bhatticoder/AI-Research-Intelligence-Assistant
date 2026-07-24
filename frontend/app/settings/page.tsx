"use client";

import { useState, useEffect } from "react";
import { GlassCard, Button, StatusBadge } from "@/components/ui";
import { obsidianApi, adminApi } from "@/lib/api";

export default function SettingsPage() {
  const [vaultPath, setVaultPath] = useState("");
  const [syncStatus, setSyncStatus] = useState<any>(null);
  const [models, setModels] = useState<any[]>([]);
  const [systemStats, setSystemStats] = useState<any>(null);
  const [newModel, setNewModel] = useState("");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    obsidianApi.status().then(setSyncStatus).catch(() => {});
    adminApi.models().then(setModels).catch(() => {});
    adminApi.system().then(setSystemStats).catch(() => {});
  }, []);

  const configureVault = async () => {
    if (!vaultPath.trim()) return;
    try {
      await obsidianApi.configure(vaultPath.trim());
      const status = await obsidianApi.status();
      setSyncStatus(status);
      alert("Vault configured successfully!");
    } catch (e: any) {
      alert(`Configuration failed: ${e.message}`);
    }
  };

  const triggerSync = async () => {
    try {
      const result = await obsidianApi.sync();
      alert(`Sync complete: ${result.new} new, ${result.modified} modified`);
      const status = await obsidianApi.status();
      setSyncStatus(status);
    } catch (e: any) {
      alert(`Sync failed: ${e.message}`);
    }
  };

  const downloadModel = async () => {
    if (!newModel.trim()) return;
    setDownloading(true);
    try {
      await adminApi.downloadModel(newModel.trim());
      const updatedModels = await adminApi.models();
      setModels(updatedModels);
      setNewModel("");
    } catch (e: any) {
      alert(`Download failed: ${e.message}`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-sm text-gray-400">Configure ARIA services and integrations</p>
      </div>

      {/* Obsidian Configuration */}
      <GlassCard className="p-6">
        <h2 className="text-lg font-semibold text-white">📓 Obsidian Integration</h2>
        <p className="mt-1 text-xs text-gray-400">Connect your Obsidian vault for automatic note syncing</p>

        <div className="mt-4 space-y-4">
          <div>
            <label className="text-xs font-medium text-gray-400">Vault Path</label>
            <div className="mt-1 flex gap-3">
              <input
                value={vaultPath}
                onChange={(e) => setVaultPath(e.target.value)}
                placeholder="C:/Users/you/Documents/MyVault"
                className="flex-1 rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:border-violet-500/50"
              />
              <Button onClick={configureVault}>Configure</Button>
            </div>
          </div>

          {syncStatus && (
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-xs text-gray-500">Status</span>
                  <p className="mt-1 font-medium text-white">
                    {syncStatus.watching ? "🟢 Watching" : syncStatus.vault_path ? "🟡 Configured" : "⚪ Not configured"}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Total Files</span>
                  <p className="mt-1 font-medium text-white">{syncStatus.total_files}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Synced</span>
                  <p className="mt-1 font-medium text-white">{syncStatus.synced_files}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Last Sync</span>
                  <p className="mt-1 font-medium text-white">
                    {syncStatus.last_sync ? new Date(syncStatus.last_sync).toLocaleString() : "Never"}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex gap-2">
                <Button variant="secondary" size="sm" onClick={triggerSync}>🔄 Sync Now</Button>
                <Button variant="ghost" size="sm" onClick={() => obsidianApi.startWatch()}>▶ Start Watch</Button>
                <Button variant="ghost" size="sm" onClick={() => obsidianApi.stopWatch()}>⏹ Stop Watch</Button>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Model Management */}
      <GlassCard className="p-6">
        <h2 className="text-lg font-semibold text-white">🤖 AI Models (Ollama)</h2>
        <p className="mt-1 text-xs text-gray-400">Manage local LLM models for chat and embeddings</p>

        <div className="mt-4 space-y-4">
          {/* Download new model */}
          <div className="flex gap-3">
            <input
              value={newModel}
              onChange={(e) => setNewModel(e.target.value)}
              placeholder="Model name (e.g., llama3.1:8b, mistral, nomic-embed-text)"
              className="flex-1 rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:border-violet-500/50"
            />
            <Button onClick={downloadModel} disabled={downloading}>
              {downloading ? "Pulling..." : "⬇️ Pull Model"}
            </Button>
          </div>

          {/* Available models */}
          <div className="space-y-2">
            {models.map((m: any) => (
              <div key={m.name} className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-white">{m.name}</p>
                  <p className="text-[10px] text-gray-500">
                    {m.family} • {m.parameters} • {(m.size / 1e9).toFixed(1)}GB
                  </p>
                </div>
                <span className="rounded-full bg-emerald-400/10 px-2.5 py-0.5 text-[10px] font-medium text-emerald-400">
                  Ready
                </span>
              </div>
            ))}
            {models.length === 0 && (
              <p className="py-4 text-center text-xs text-gray-500">No models found. Pull a model to get started.</p>
            )}
          </div>
        </div>
      </GlassCard>

      {/* System Stats */}
      {systemStats && (
        <GlassCard className="p-6">
          <h2 className="text-lg font-semibold text-white">⚡ System Status</h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
              <p className="text-xs text-gray-500">Ollama</p>
              <p className={`mt-1 text-sm font-semibold ${systemStats.ollama?.status === "healthy" ? "text-emerald-400" : "text-red-400"}`}>
                {systemStats.ollama?.status || "Unknown"}
              </p>
              <p className="mt-1 text-[10px] text-gray-500">
                Chat: {systemStats.ollama?.chat_model || "N/A"}
              </p>
            </div>
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
              <p className="text-xs text-gray-500">ChromaDB</p>
              <p className="mt-1 text-sm font-semibold text-white">
                {systemStats.chromadb?.total_chunks || 0} chunks
              </p>
              <p className="mt-1 text-[10px] text-gray-500">
                Collection: {systemStats.chromadb?.collection_name || "N/A"}
              </p>
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
