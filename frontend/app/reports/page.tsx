"use client";

import { useState, useEffect } from "react";
import { GlassCard, Button, EmptyState } from "@/components/ui";
import { reportsApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [showGenerator, setShowGenerator] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatedReport, setGeneratedReport] = useState<any>(null);

  // Form state
  const [query, setQuery] = useState("");
  const [title, setTitle] = useState("");
  const [template, setTemplate] = useState("default");
  const [format, setFormat] = useState("markdown");

  useEffect(() => {
    reportsApi.list().then(setReports).catch(() => {});
    reportsApi.templates().then(setTemplates).catch(() => {});
  }, []);

  const generateReport = async () => {
    if (!query.trim()) return;
    setGenerating(true);
    setGeneratedReport(null);

    try {
      const result = await reportsApi.generate({
        query: query.trim(),
        title: title.trim() || undefined,
        template,
        format,
      });
      setGeneratedReport(result);
      setReports((prev) => [result, ...prev]);
    } catch (e: any) {
      alert(`Report generation failed: ${e.message}`);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Reports</h1>
          <p className="text-sm text-gray-400">Generate research reports from your knowledge base</p>
        </div>
        <Button variant="primary" onClick={() => setShowGenerator(!showGenerator)}>
          {showGenerator ? "Close" : "📋 New Report"}
        </Button>
      </div>

      {/* Report Generator */}
      {showGenerator && (
        <GlassCard className="p-6">
          <h2 className="text-lg font-semibold text-white">Generate Report</h2>
          <p className="mt-1 text-xs text-gray-400">
            ARIA will search your documents and generate a comprehensive report
          </p>

          <div className="mt-6 space-y-4">
            <div>
              <label className="text-xs font-medium text-gray-400">Research Question / Query *</label>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What are the key findings about..."
                rows={3}
                className="mt-1 w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-3 text-sm text-white placeholder-gray-500 outline-none focus:border-violet-500/50"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-gray-400">Report Title (optional)</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Auto-generated if empty"
                className="mt-1 w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:border-violet-500/50"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-400">Template</label>
                <select
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2.5 text-sm text-white outline-none"
                >
                  {templates.map((t: any) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-400">Format</label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2.5 text-sm text-white outline-none"
                >
                  <option value="markdown">Markdown</option>
                  <option value="pdf">PDF</option>
                </select>
              </div>
            </div>

            <Button onClick={generateReport} disabled={generating || !query.trim()} size="lg" className="w-full">
              {generating ? "⏳ Generating report..." : "🚀 Generate Report"}
            </Button>
          </div>
        </GlassCard>
      )}

      {/* Generated Report Preview */}
      {generatedReport && (
        <GlassCard className="p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">{generatedReport.title}</h3>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => window.open(reportsApi.download(generatedReport.id), "_blank")}
            >
              📥 Download
            </Button>
          </div>
          <div className="mt-4 max-h-96 overflow-y-auto rounded-xl border border-white/[0.06] bg-black/30 p-4">
            <pre className="whitespace-pre-wrap text-xs leading-relaxed text-gray-300">
              {generatedReport.content}
            </pre>
          </div>
        </GlassCard>
      )}

      {/* Reports List */}
      {reports.length === 0 && !showGenerator ? (
        <EmptyState
          icon="📋"
          title="No reports yet"
          description="Generate your first report by clicking 'New Report'. ARIA will compile insights from your documents."
          action={<Button onClick={() => setShowGenerator(true)}>Create Report</Button>}
        />
      ) : (
        <div className="space-y-3">
          {reports.map((report: any) => (
            <GlassCard key={report.id} className="flex items-center justify-between p-4">
              <div>
                <h3 className="text-sm font-semibold text-white">{report.title}</h3>
                <div className="mt-1 flex items-center gap-3 text-[10px] text-gray-500">
                  <span>{report.format?.toUpperCase()}</span>
                  <span>{report.template}</span>
                  <span>{formatDate(report.created_at)}</span>
                </div>
                {report.query && (
                  <p className="mt-1 text-xs text-gray-400 line-clamp-1">Query: {report.query}</p>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => window.open(reportsApi.download(report.id), "_blank")}
              >
                📥
              </Button>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
