"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUIStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "📊", description: "Overview & stats" },
  { href: "/chat", label: "AI Chat", icon: "💬", description: "Ask your knowledge base" },
  { href: "/documents", label: "Documents", icon: "📁", description: "Upload & manage" },
  { href: "/graph", label: "Knowledge Graph", icon: "🕸️", description: "Explore connections" },
  { href: "/reports", label: "Reports", icon: "📋", description: "Generate reports" },
  { href: "/news", label: "News & Papers", icon: "📰", description: "Research feed" },
  { href: "/settings", label: "Settings", icon: "⚙️", description: "Configuration" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen border-r border-white/[0.06] bg-[#0a0a0f]/95 backdrop-blur-2xl transition-all duration-300",
        sidebarOpen ? "w-64" : "w-20"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b border-white/[0.06] px-4">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 text-xl font-bold shadow-lg shadow-violet-500/25">
            A
          </div>
          {sidebarOpen && (
            <div className="overflow-hidden">
              <h1 className="text-lg font-bold tracking-tight text-white">ARIA</h1>
              <p className="text-[10px] font-medium uppercase tracking-widest text-violet-400">
                Research AI
              </p>
            </div>
          )}
        </Link>
        <button
          onClick={toggleSidebar}
          className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-white/5 hover:text-white"
        >
          {sidebarOpen ? "◀" : "▶"}
        </button>
      </div>

      {/* Navigation */}
      <nav className="mt-4 flex flex-col gap-1 px-3">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-gradient-to-r from-violet-500/15 to-indigo-500/10 text-white shadow-sm"
                  : "text-gray-400 hover:bg-white/[0.04] hover:text-gray-200"
              )}
            >
              {/* Active indicator */}
              {isActive && (
                <div className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-violet-400 to-indigo-500" />
              )}

              <span className="text-lg">{item.icon}</span>

              {sidebarOpen && (
                <div className="overflow-hidden">
                  <span className="block">{item.label}</span>
                  <span className="block text-[10px] font-normal text-gray-500 group-hover:text-gray-400">
                    {item.description}
                  </span>
                </div>
              )}

              {/* Tooltip for collapsed sidebar */}
              {!sidebarOpen && (
                <div className="pointer-events-none absolute left-full ml-2 rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-medium text-white opacity-0 shadow-xl transition-opacity group-hover:opacity-100 whitespace-nowrap">
                  {item.label}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="absolute bottom-4 left-0 right-0 px-3">
        <div className={cn(
          "rounded-xl border border-white/[0.06] bg-gradient-to-br from-violet-500/5 to-indigo-500/5 p-3",
          !sidebarOpen && "p-2"
        )}>
          {sidebarOpen ? (
            <>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-emerald-400 shadow-lg shadow-emerald-400/50" />
                <span className="text-xs font-medium text-emerald-400">System Online</span>
              </div>
              <p className="mt-1 text-[10px] text-gray-500">Ollama • ChromaDB • PostgreSQL</p>
            </>
          ) : (
            <div className="flex justify-center">
              <div className="h-2 w-2 rounded-full bg-emerald-400 shadow-lg shadow-emerald-400/50" />
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
