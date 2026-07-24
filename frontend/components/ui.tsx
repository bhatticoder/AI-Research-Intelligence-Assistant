"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  trend?: { value: number; label: string };
  gradient: string;
  className?: string;
}

export function StatsCard({ title, value, subtitle, icon, trend, gradient, className }: StatsCardProps) {
  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-white/[0.06] bg-[#12121a] p-6 transition-all duration-300 hover:border-white/[0.1] hover:shadow-2xl",
        className
      )}
    >
      {/* Gradient glow */}
      <div className={cn("absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-20 blur-2xl transition-opacity group-hover:opacity-40", gradient)} />

      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">{title}</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-gray-400">{subtitle}</p>}
          {trend && (
            <div className="mt-2 flex items-center gap-1">
              <span className={cn(
                "text-xs font-semibold",
                trend.value >= 0 ? "text-emerald-400" : "text-red-400"
              )}>
                {trend.value >= 0 ? "↑" : "↓"} {Math.abs(trend.value)}%
              </span>
              <span className="text-[10px] text-gray-500">{trend.label}</span>
            </div>
          )}
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/[0.04] text-2xl">
          {icon}
        </div>
      </div>
    </div>
  );
}

// ── Status Badge ─────────────────────────────────────────────

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  const config: Record<string, { bg: string; text: string; dot: string }> = {
    completed: { bg: "bg-emerald-400/10", text: "text-emerald-400", dot: "bg-emerald-400" },
    processing: { bg: "bg-amber-400/10", text: "text-amber-400", dot: "bg-amber-400" },
    embedding: { bg: "bg-blue-400/10", text: "text-blue-400", dot: "bg-blue-400" },
    pending: { bg: "bg-gray-400/10", text: "text-gray-400", dot: "bg-gray-400" },
    failed: { bg: "bg-red-400/10", text: "text-red-400", dot: "bg-red-400" },
    running_ocr: { bg: "bg-purple-400/10", text: "text-purple-400", dot: "bg-purple-400" },
    extracting_text: { bg: "bg-cyan-400/10", text: "text-cyan-400", dot: "bg-cyan-400" },
    chunking: { bg: "bg-indigo-400/10", text: "text-indigo-400", dot: "bg-indigo-400" },
  };
  const c = config[status] || config.pending;

  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-full font-medium",
      c.bg, c.text,
      size === "sm" ? "px-2.5 py-0.5 text-[10px]" : "px-3 py-1 text-xs"
    )}>
      <span className={cn("h-1.5 w-1.5 rounded-full", c.dot, status === "processing" && "animate-pulse")} />
      {status.replace(/_/g, " ")}
    </span>
  );
}

// ── Glass Card ───────────────────────────────────────────────

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}

export function GlassCard({ children, className, hover = true }: GlassCardProps) {
  return (
    <div className={cn(
      "rounded-2xl border border-white/[0.06] bg-[#12121a]/80 backdrop-blur-sm",
      hover && "transition-all duration-300 hover:border-white/[0.1] hover:shadow-xl hover:shadow-violet-500/5",
      className
    )}>
      {children}
    </div>
  );
}

// ── Empty State ──────────────────────────────────────────────

interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-5xl">{icon}</div>
      <h3 className="mt-4 text-lg font-semibold text-white">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-gray-400">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

// ── Button ───────────────────────────────────────────────────

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  children: ReactNode;
}

export function Button({ variant = "primary", size = "md", children, className, ...props }: ButtonProps) {
  const variants = {
    primary: "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 hover:from-violet-500 hover:to-indigo-500",
    secondary: "bg-white/[0.06] text-gray-200 border border-white/[0.1] hover:bg-white/[0.1] hover:text-white",
    ghost: "text-gray-400 hover:bg-white/[0.04] hover:text-white",
    danger: "bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20",
  };
  const sizes = {
    sm: "px-3 py-1.5 text-xs rounded-lg",
    md: "px-4 py-2 text-sm rounded-xl",
    lg: "px-6 py-3 text-base rounded-xl",
  };

  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 font-medium transition-all duration-200 disabled:opacity-50 disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
