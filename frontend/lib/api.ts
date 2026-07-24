/**
 * ARIA API Client - Centralized HTTP client with auth interceptors.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8080";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("aria_token");
}

function setToken(token: string) { localStorage.setItem("aria_token", token); }
function removeToken() { localStorage.removeItem("aria_token"); }

async function apiFetch<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (options.body) {
    headers["Content-Type"] = "application/json";
  }
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  } catch (err) {
    throw new Error("Cannot connect to the backend server. Make sure it is running on port 8080.");
  }

  if (res.status === 401) {
    removeToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API Error: ${res.status}`);
  }
  // else {
  //   console.log(res);
  // }
  return res.json();
}

async function apiUpload<T = any>(endpoint: string, formData: FormData): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const targetUrl = `${API_BASE}${endpoint}`;
  console.group(`🚀 [API Upload] POST ${targetUrl}`);
  console.log("⏰ Timestamp:", new Date().toISOString());
  console.log("🔑 Auth Token Present:", !!token);

  for (const [key, value] of formData.entries()) {
    if (value instanceof File) {
      console.log(`📁 FormData file key "${key}":`, {
        name: value.name,
        sizeBytes: value.size,
        sizeMB: (value.size / (1024 * 1024)).toFixed(2) + " MB",
        type: value.type,
        lastModified: new Date(value.lastModified).toISOString()
      });
    } else {
      console.log(`📝 FormData field key "${key}":`, value);
    }
  }

  let res: Response;
  const startTime = performance.now();
  try {
    res = await fetch(targetUrl, { method: "POST", headers, body: formData });
    const duration = (performance.now() - startTime).toFixed(2);
    console.log(`📡 HTTP Response Status: ${res.status} ${res.statusText} (${duration}ms)`);
  } catch (err: any) {
    console.error("❌ Network Connection Error during upload:", err);
    console.groupEnd();
    throw new Error("Cannot connect to the backend server. Make sure it is running on port 8080.");
  }

  if (res.status === 401) {
    console.warn("🔒 401 Unauthorized - Token expired or invalid. Redirecting to login...");
    console.groupEnd();
    removeToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    console.error(`❌ Upload Error HTTP ${res.status}:`, error);
    console.groupEnd();
    throw new Error(error.detail || `Upload Error: ${res.status}`);
  }

  const result = await res.json();
  console.log("✅ Upload Succeeded! Server Response Payload:", result);
  console.groupEnd();
  return result;
}

export const authApi = {
  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    apiFetch("/api/auth/register", { method: "POST", body: JSON.stringify(data) }).then((res) => {
      if (res?.access_token) setToken(res.access_token);
      return res;
    }),
  login: (username: string, password: string) => {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    return fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Invalid credentials" }));
        throw new Error(err.detail || "Invalid credentials");
      }
      const data = await res.json();
      if (data?.access_token) setToken(data.access_token);
      return data;
    });
  },
  me: () => apiFetch("/api/auth/me"),
  setToken, removeToken, getToken,
};

export const documentsApi = {
  upload: (file: File) => { const form = new FormData(); form.append("file", file); return apiUpload("/api/documents/upload", form); },
  list: (params?: { page?: number; page_size?: number; search?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    if (params?.search) qs.set("search", params.search);
    if (params?.status) qs.set("status", params.status);
    return apiFetch(`/api/documents?${qs}`);
  },
  get: (id: string) => apiFetch(`/api/documents/${id}`),
  delete: (id: string) => apiFetch(`/api/documents/${id}?_t=${Date.now()}`, { method: "DELETE" }),
  process: (id: string) => apiFetch(`/api/documents/${id}/process`, { method: "POST" }),
};

export const chatApi = {
  send: (data: { message: string; conversation_id?: string; model?: string; n_results?: number }) =>
    apiFetch("/api/chat", { method: "POST", body: JSON.stringify(data) }),
  history: () => apiFetch("/api/chat/history"),
  messages: (conversationId: string) => apiFetch(`/api/chat/${conversationId}/messages`),
  clear: (conversationId: string) => apiFetch(`/api/chat/${conversationId}/clear`, { method: "POST" }),
};

export const obsidianApi = {
  status: () => apiFetch("/api/obsidian/status"),
  sync: () => apiFetch("/api/obsidian/sync", { method: "POST" }),
  stats: () => apiFetch("/api/obsidian/stats"),
  configure: (vaultPath: string) => apiFetch("/api/obsidian/configure", { method: "POST", body: JSON.stringify({ vault_path: vaultPath }) }),
  startWatch: () => apiFetch("/api/obsidian/watch/start", { method: "POST" }),
  stopWatch: () => apiFetch("/api/obsidian/watch/stop", { method: "POST" }),
};

export const graphApi = {
  nodes: () => apiFetch("/api/graph/nodes"),
  connections: (entity: string, depth?: number) => apiFetch(`/api/graph/connections/${encodeURIComponent(entity)}?depth=${depth || 2}`),
  central: (topN?: number) => apiFetch(`/api/graph/central?top_n=${topN || 20}`),
  related: (docId: string) => apiFetch(`/api/graph/related/${docId}`),
};

export const reportsApi = {
  generate: (data: { query: string; title?: string; template?: string; format?: string }) =>
    apiFetch("/api/reports/generate", { method: "POST", body: JSON.stringify(data) }),
  list: () => apiFetch("/api/reports"),
  download: (id: string) => `${API_BASE}/api/reports/${id}/download`,
  templates: () => apiFetch("/api/reports/templates"),
};

export const adminApi = {
  models: () => apiFetch("/api/admin/models"),
  downloadModel: (modelName: string) => apiFetch("/api/admin/models/download", { method: "POST", body: JSON.stringify({ model_name: modelName }) }),
  system: () => apiFetch("/api/admin/system"),
  searchNews: (query: string, maxResults?: number) => apiFetch("/api/admin/news/search", { method: "POST", body: JSON.stringify({ query, max_results: maxResults || 10 }) }),
  searchArxiv: (query: string, maxResults?: number) => apiFetch("/api/admin/news/arxiv", { method: "POST", body: JSON.stringify({ query, max_results: maxResults || 10 }) }),
  briefing: (topics: string[]) => apiFetch("/api/admin/news/briefing", { method: "POST", body: JSON.stringify({ topics }) }),
};

export function createChatWebSocket(
  onToken: (token: string) => void,
  onSources: (sources: any[]) => void,
  onDone: () => void,
  onError: (error: string) => void
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/chat`);
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    switch (data.type) {
      case "token": onToken(data.content); break;
      case "sources": onSources(data.sources); break;
      case "done": onDone(); break;
      case "error": onError(data.content); break;
    }
  };
  ws.onerror = () => onError("WebSocket connection failed");
  return ws;
}

export { API_BASE, WS_BASE };
