"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { Button, GlassCard } from "@/components/ui";

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: "",
    username: "",
    password: "",
    full_name: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    
    try {
      const res = await authApi.register(formData);
      authApi.setToken(res.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to register. Username or email might be taken.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-[#0a0a0f] p-4 absolute top-0 left-0 z-50 overflow-y-auto">
      <div className="absolute inset-0 bg-gradient-to-br from-violet-500/10 to-indigo-500/10 blur-3xl pointer-events-none" />
      
      <div className="w-full max-w-md relative z-10 my-8">
        <div className="text-center mb-8">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 text-3xl font-bold shadow-lg shadow-violet-500/25 mb-4">
            A
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Create Account</h1>
          <p className="mt-2 text-gray-400">Join ARIA to manage your research</p>
        </div>

        <GlassCard className="p-8">
          <form onSubmit={handleRegister} className="flex flex-col gap-4">
            {error && (
              <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-400">
                {error}
              </div>
            )}
            
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-300">Full Name</label>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                className="rounded-xl border border-white/[0.06] bg-[#12121a] px-4 py-3 text-white placeholder-gray-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 transition-colors"
                placeholder="John Doe"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-300">Email</label>
              <input
                type="email"
                name="email"
                required
                value={formData.email}
                onChange={handleChange}
                className="rounded-xl border border-white/[0.06] bg-[#12121a] px-4 py-3 text-white placeholder-gray-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 transition-colors"
                placeholder="john@example.com"
              />
            </div>
            
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-300">Username</label>
              <input
                type="text"
                name="username"
                required
                value={formData.username}
                onChange={handleChange}
                className="rounded-xl border border-white/[0.06] bg-[#12121a] px-4 py-3 text-white placeholder-gray-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 transition-colors"
                placeholder="johndoe"
              />
            </div>
            
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-300">Password</label>
              <input
                type="password"
                name="password"
                required
                value={formData.password}
                onChange={handleChange}
                className="rounded-xl border border-white/[0.06] bg-[#12121a] px-4 py-3 text-white placeholder-gray-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 transition-colors"
                placeholder="Create a strong password"
              />
            </div>
            
            <Button type="submit" size="lg" className="mt-4 w-full" disabled={loading}>
              {loading ? "Creating account..." : "Register"}
            </Button>

            <div className="mt-4 text-center text-sm text-gray-400">
              Already have an account?{" "}
              <a href="/login" className="text-violet-400 hover:text-violet-300 font-medium">
                Sign in
              </a>
            </div>
          </form>
        </GlassCard>
      </div>
    </div>
  );
}
