"use client";

import { useState, useEffect } from "react";
import { GlassCard, Button, EmptyState } from "@/components/ui";
import { adminApi } from "@/lib/api";

export default function NewsPage() {
  const [activeTab, setActiveTab] = useState<"arxiv" | "news">("arxiv");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = activeTab === "arxiv"
        ? await adminApi.searchArxiv(query.trim(), 15)
        : await adminApi.searchNews(query.trim(), 15);
      setResults(data);
    } catch (e: any) {
      alert(`Search failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">News & Papers</h1>
        <p className="text-sm text-gray-400">Discover research papers and news for your knowledge base</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {(["arxiv", "news"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); setResults([]); }}
            className={`rounded-xl px-4 py-2 text-sm font-medium transition-all ${
              activeTab === tab
                ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/25"
                : "bg-white/[0.04] text-gray-400 hover:text-white"
            }`}
          >
            {tab === "arxiv" ? "📚 arXiv Papers" : "📰 News Articles"}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder={activeTab === "arxiv" ? "Search arXiv papers..." : "Search news articles..."}
          className="flex-1 rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:border-violet-500/50"
        />
        <Button onClick={search} disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Search"}
        </Button>
      </div>

      {/* Results */}
      {results.length === 0 && !loading ? (
        <EmptyState
          icon={activeTab === "arxiv" ? "📚" : "📰"}
          title={`Search ${activeTab === "arxiv" ? "arXiv" : "News"}`}
          description={`Enter a query to search for ${activeTab === "arxiv" ? "research papers" : "news articles"}`}
        />
      ) : (
        <div className="space-y-3">
          {results.map((item: any, i: number) => (
            <GlassCard key={i} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-white leading-snug">{item.title}</h3>

                  {/* arXiv metadata */}
                  {item.authors && (
                    <p className="mt-1.5 text-[11px] text-gray-500">
                      {item.authors.slice(0, 4).join(", ")}
                      {item.authors.length > 4 ? ` +${item.authors.length - 4} more` : ""}
                    </p>
                  )}

                  {/* News metadata */}
                  {item.source && !item.arxiv_id && (
                    <p className="mt-1 text-[11px] text-gray-500">
                      {item.source} • {item.author || "Unknown author"}
                    </p>
                  )}

                  <p className="mt-2 text-xs leading-relaxed text-gray-400 line-clamp-3">
                    {item.summary || item.description || item.content || "No description available"}
                  </p>

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {item.categories?.map((cat: string) => (
                      <span key={cat} className="rounded-full bg-violet-500/10 px-2.5 py-0.5 text-[9px] font-medium text-violet-400">
                        {cat}
                      </span>
                    ))}
                    {item.published && (
                      <span className="text-[10px] text-gray-500">
                        {new Date(item.published || item.published_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-shrink-0 flex-col gap-2">
                  {item.pdf_url && (
                    <a href={item.pdf_url} target="_blank" rel="noopener noreferrer">
                      <Button variant="secondary" size="sm">📄 PDF</Button>
                    </a>
                  )}
                  {item.url && (
                    <a href={item.url} target="_blank" rel="noopener noreferrer">
                      <Button variant="ghost" size="sm">🔗 Open</Button>
                    </a>
                  )}
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
