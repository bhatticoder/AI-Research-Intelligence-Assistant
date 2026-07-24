import { create } from "zustand";

interface User { id: string; email: string; username: string; full_name?: string; is_admin: boolean; }

interface AuthState {
  user: User | null; token: string | null; isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void; logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== "undefined" ? localStorage.getItem("aria_token") : null,
  isAuthenticated: typeof window !== "undefined" ? !!localStorage.getItem("aria_token") : false,
  setAuth: (user, token) => { localStorage.setItem("aria_token", token); set({ user, token, isAuthenticated: true }); },
  logout: () => { localStorage.removeItem("aria_token"); set({ user: null, token: null, isAuthenticated: false }); },
}));

interface UIState { sidebarOpen: boolean; activeView: string; toggleSidebar: () => void; setActiveView: (view: string) => void; }

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true, activeView: "dashboard",
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setActiveView: (view) => set({ activeView: view }),
}));

interface ChatMessage { id: string; role: "user" | "assistant"; content: string; sources?: any[]; isStreaming?: boolean; timestamp: Date; }

interface ChatState {
  messages: ChatMessage[]; conversationId: string | null; isLoading: boolean; streamingContent: string;
  addMessage: (msg: ChatMessage) => void; updateLastMessage: (content: string) => void;
  setConversationId: (id: string | null) => void; setLoading: (loading: boolean) => void;
  setStreamingContent: (content: string) => void; appendStreamingContent: (token: string) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [], conversationId: null, isLoading: false, streamingContent: "",
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateLastMessage: (content) => set((s) => ({ messages: s.messages.map((m, i) => i === s.messages.length - 1 ? { ...m, content, isStreaming: false } : m) })),
  setConversationId: (id) => set({ conversationId: id }),
  setLoading: (loading) => set({ isLoading: loading }),
  setStreamingContent: (content) => set({ streamingContent: content }),
  appendStreamingContent: (token) => set((s) => ({ streamingContent: s.streamingContent + token })),
  clearMessages: () => set({ messages: [], conversationId: null, streamingContent: "" }),
}));
