"use client";

import { ReactNode } from "react";
import Sidebar from "@/components/Sidebar";
import { useUIStore } from "@/lib/store";
import { cn } from "@/lib/utils";

import { usePathname } from "next/navigation";

export default function LayoutWrapper({ children }: { children: ReactNode }) {
  const { sidebarOpen } = useUIStore();
  const pathname = usePathname();
  
  const isAuthPage = pathname === "/login" || pathname === "/register";

  if (isAuthPage) {
    return <main className="flex-1 overflow-y-auto">{children}</main>;
  }

  return (
    <div className="flex h-screen bg-[#0a0a0f] text-gray-200 overflow-hidden">
      <Sidebar />
      <main
        className={cn(
          "flex-1 overflow-y-auto transition-all duration-300 p-8",
          sidebarOpen ? "ml-64" : "ml-20"
        )}
      >
        {children}
      </main>
    </div>
  );
}
