"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { Button, GlassCard } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    
    try {
      const res = await authApi.login(username, password);
      authApi.setToken(res.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to login. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-[#0a0a0f] p-4 absolute top-0 left-0 z-50">
      <div className="absolute inset-0 bg-gradient-to-br from-violet-500/10 to-indigo-500/10 blur-3xl pointer-events-none" />
      
      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 text-3xl font-bold shadow-lg shadow-violet-500/25 mb-4">
            A
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Welcome back</h1>
          <p className="mt-2 text-gray-400">Sign in to your ARIA account</p>
        </div>

        <GlassCard className="p-8">
          <form onSubmit={handleLogin} className="flex flex-col gap-5">
            {error && (
              <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-400">
                {error}
              </div>
            )}
            
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-300">Username or Email</label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="rounded-xl border border-white/[0.06] bg-[#12121a] px-4 py-3 text-white placeholder-gray-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 transition-colors"
                placeholder="Enter your username"
              />
            </div>
            
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-300">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="rounded-xl border border-white/[0.06] bg-[#12121a] px-4 py-3 text-white placeholder-gray-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 transition-colors"
                placeholder="Enter your password"
              />
            </div>
            
            <Button type="submit" size="lg" className="mt-2 w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </Button>

            <div className="mt-4 text-center text-sm text-gray-400">
              Don't have an account?{" "}
              <a href="/register" className="text-violet-400 hover:text-violet-300 font-medium">
                Create one
              </a>
            </div>
          </form>
        </GlassCard>
      </div>
    </div>
  );
}
