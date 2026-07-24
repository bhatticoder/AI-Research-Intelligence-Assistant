"use client";

import { useState, useEffect, useRef } from "react";
import { GlassCard, Button, EmptyState } from "@/components/ui";
import { graphApi } from "@/lib/api";

export default function GraphPage() {
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  const [centralEntities, setCentralEntities] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [connections, setConnections] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    async function load() {
      try {
        const [graph, central] = await Promise.all([
          graphApi.nodes(),
          graphApi.central(30),
        ]);
        setGraphData(graph);
        setCentralEntities(central);
      } catch (e) {
        console.error("Graph load error:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (!canvasRef.current || graphData.nodes.length === 0) return;
    drawGraph();
  }, [graphData, selectedNode]);

  const drawGraph = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.parentElement?.getBoundingClientRect();
    canvas.width = rect?.width || 800;
    canvas.height = rect?.height || 600;

    ctx.fillStyle = "#0a0a0f";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const nodes = graphData.nodes;
    const edges = graphData.edges;

    // Position nodes using simple force layout
    const positions: Record<string, { x: number; y: number }> = {};
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / nodes.length;
      const radius = Math.min(cx, cy) * 0.7;
      positions[node.id] = {
        x: cx + radius * Math.cos(angle) + (Math.random() - 0.5) * 50,
        y: cy + radius * Math.sin(angle) + (Math.random() - 0.5) * 50,
      };
    });

    // Draw edges
    edges.forEach((edge) => {
      const from = positions[edge.source];
      const to = positions[edge.target];
      if (!from || !to) return;

      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.strokeStyle = `rgba(139, 92, 246, ${Math.min(edge.weight * 0.15, 0.5)})`;
      ctx.lineWidth = Math.min(edge.weight, 3);
      ctx.stroke();
    });

    // Draw nodes
    const typeColors: Record<string, string> = {
      persons: "#a78bfa",
      organizations: "#60a5fa",
      concepts: "#34d399",
      technologies: "#f472b6",
      locations: "#fbbf24",
      dates: "#fb923c",
    };

    nodes.forEach((node) => {
      const pos = positions[node.id];
      if (!pos) return;

      const size = Math.max(4, Math.min(node.degree * 2, 16));
      const color = typeColors[node.type] || "#9ca3af";
      const isSelected = selectedNode?.id === node.id;

      // Glow effect
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, size + 8, 0, Math.PI * 2);
        ctx.fillStyle = `${color}33`;
        ctx.fill();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, size, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      // Label
      if (node.degree > 2 || isSelected) {
        ctx.fillStyle = "#e5e7eb";
        ctx.font = `${isSelected ? "bold " : ""}${isSelected ? 12 : 10}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.fillText(node.label, pos.x, pos.y - size - 6);
      }
    });
  };

  const handleNodeClick = async (entity: string) => {
    try {
      const conn = await graphApi.connections(entity, 2);
      setSelectedNode(conn);
      setConnections(conn);
    } catch (e) {
      console.error("Failed to get connections:", e);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Knowledge Graph</h1>
        <p className="text-sm text-gray-400">
          Explore connections between entities across your documents
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Graph Canvas */}
        <div className="lg:col-span-3">
          <GlassCard className="relative h-[600px] overflow-hidden p-0">
            {graphData.nodes.length === 0 && !loading ? (
              <EmptyState
                icon="🕸️"
                title="No graph data yet"
                description="Upload and process documents to build your knowledge graph. ARIA automatically extracts entities and finds connections."
              />
            ) : (
              <canvas ref={canvasRef} className="h-full w-full" />
            )}

            {/* Legend */}
            <div className="absolute bottom-4 left-4 rounded-lg border border-white/[0.06] bg-black/80 p-3 backdrop-blur-sm">
              <p className="text-[10px] font-medium text-gray-400">Entity Types</p>
              <div className="mt-1 grid grid-cols-3 gap-x-3 gap-y-1">
                {[
                  { label: "Persons", color: "#a78bfa" },
                  { label: "Organizations", color: "#60a5fa" },
                  { label: "Concepts", color: "#34d399" },
                  { label: "Technologies", color: "#f472b6" },
                  { label: "Locations", color: "#fbbf24" },
                  { label: "Dates", color: "#fb923c" },
                ].map((t) => (
                  <div key={t.label} className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: t.color }} />
                    <span className="text-[9px] text-gray-400">{t.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Stats */}
            <div className="absolute right-4 top-4 rounded-lg border border-white/[0.06] bg-black/80 p-3 backdrop-blur-sm">
              <p className="text-xs text-gray-400">
                {graphData.nodes.length} entities • {graphData.edges.length} connections
              </p>
            </div>
          </GlassCard>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Central Entities */}
          <GlassCard className="p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Top Entities</h3>
            <div className="mt-3 space-y-2">
              {centralEntities.slice(0, 15).map((e: any, idx: number) => (
                <button
                  key={`${e.label}-${idx}`}
                  onClick={() => handleNodeClick(e.label)}
                  className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-white/[0.04]"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500">{e.connections}</span>
                    <span className="text-xs text-gray-200 truncate max-w-[120px]">{e.label}</span>
                  </div>
                  <span className="text-[9px] text-gray-500">{e.type}</span>
                </button>
              ))}
            </div>
          </GlassCard>

          {/* Selected Node Details */}
          {connections && (
            <GlassCard className="p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Connections: {connections.entity}
              </h3>
              <p className="mt-1 text-[10px] text-gray-500">
                Type: {connections.type} • {connections.total} connections
              </p>
              <div className="mt-3 space-y-1.5">
                {connections.connections?.slice(0, 10).map((c: any, i: number) => (
                  <div key={i} className="rounded-lg bg-white/[0.02] px-2 py-1.5">
                    <p className="text-xs text-gray-300">{c.entity}</p>
                    <p className="text-[9px] text-gray-500">
                      {c.relation} • weight: {c.weight}
                    </p>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}
        </div>
      </div>
    </div>
  );
}
