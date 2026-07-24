"use client";

import { useState, useRef, useEffect } from "react";
import { GlassCard, Button, EmptyState } from "@/components/ui";
import { chatApi, createChatWebSocket } from "@/lib/api";
import { useChatStore } from "@/lib/store";

export default function ChatPage() {
  const {
    messages, isLoading, streamingContent, conversationId,
    addMessage, setLoading, setStreamingContent, appendStreamingContent,
    setConversationId, clearMessages, updateLastMessage,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [useStreaming, setUseStreaming] = useState(false);
  const [sources, setSources] = useState<any[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    chatApi.history().then(setConversations).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg = input.trim();
    setInput("");
    setSources([]);

    addMessage({
      id: Date.now().toString(),
      role: "user",
      content: userMsg,
      timestamp: new Date(),
    });
    setLoading(true);

    if (useStreaming) {
      // WebSocket streaming
      setStreamingContent("");
      addMessage({
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "",
        isStreaming: true,
        timestamp: new Date(),
      });

      const ws = createChatWebSocket(
        (token) => appendStreamingContent(token),
        (srcs) => setSources(srcs),
        () => {
          updateLastMessage(useChatStore.getState().streamingContent);
          setStreamingContent("");
          setLoading(false);
        },
        (error) => {
          updateLastMessage(`Error: ${error}`);
          setLoading(false);
        }
      );

      ws.onopen = () => {
        ws.send(JSON.stringify({ message: userMsg, n_results: 5 }));
      };
    } else {
      // REST API
      try {
        const result = await chatApi.send({
          message: userMsg,
          conversation_id: conversationId || undefined,
        });

        addMessage({
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: result.answer,
          sources: result.sources,
          timestamp: new Date(),
        });
        setSources(result.sources || []);
        setConversationId(result.conversation_id);
      } catch (e: any) {
        addMessage({
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: `Error: ${e.message}`,
          timestamp: new Date(),
        });
      } finally {
        setLoading(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const loadConversation = async (convoId: string) => {
    try {
      clearMessages();
      const msgs = await chatApi.messages(convoId);
      setConversationId(convoId);
      msgs.forEach((m: any) => {
        addMessage({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources,
          timestamp: new Date(m.created_at),
        });
      });
    } catch (e) {
      console.error("Failed to load conversation:", e);
    }
  };

  return (
    <div className="flex h-[calc(100vh-5rem)] gap-4">
      {/* Conversation Sidebar */}
      <div className="hidden w-64 flex-shrink-0 lg:block">
        <GlassCard className="flex h-full flex-col p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">History</h3>
            <Button variant="ghost" size="sm" onClick={() => { clearMessages(); setSources([]); }}>
              + New
            </Button>
          </div>
          <div className="mt-3 flex-1 space-y-1 overflow-y-auto">
            {conversations.map((c: any) => (
              <button
                key={c.id}
                onClick={() => loadConversation(c.id)}
                className={`w-full rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                  conversationId === c.id
                    ? "bg-violet-500/10 text-violet-300"
                    : "text-gray-400 hover:bg-white/[0.04] hover:text-gray-200"
                }`}
              >
                <p className="truncate font-medium">{c.title}</p>
                <p className="mt-0.5 text-[10px] text-gray-500">{c.message_count} messages</p>
              </button>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col">
        <GlassCard className="flex flex-1 flex-col overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6">
            {messages.length === 0 ? (
              <EmptyState
                icon="🧠"
                title="Ask ARIA anything"
                description="Ask questions about your documents. ARIA will search your knowledge base and provide answers with source citations."
              />
            ) : (
              <div className="space-y-6">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
                    {msg.role === "assistant" && (
                      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 text-sm font-bold">
                        A
                      </div>
                    )}
                    <div
                      className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white"
                          : "border border-white/[0.06] bg-white/[0.03] text-gray-200"
                      }`}
                    >
                      <div className="whitespace-pre-wrap">
                        {msg.isStreaming ? streamingContent || "..." : msg.content}
                      </div>
                    </div>
                  </div>
                ))}
                {isLoading && !useStreaming && (
                  <div className="flex gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 text-sm font-bold">A</div>
                    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-4 py-3">
                      <div className="flex gap-1">
                        <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400" style={{ animationDelay: "0ms" }} />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400" style={{ animationDelay: "150ms" }} />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="border-t border-white/[0.06] p-4">
            <div className="flex gap-3">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your documents..."
                rows={1}
                className="flex-1 resize-none rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition-colors focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/25"
              />
              <Button onClick={sendMessage} disabled={isLoading || !input.trim()} size="lg">
                {isLoading ? "..." : "Send"}
              </Button>
            </div>
            <div className="mt-2 flex items-center gap-4">
              <label className="flex items-center gap-2 text-[10px] text-gray-500">
                <input
                  type="checkbox"
                  checked={useStreaming}
                  onChange={(e) => setUseStreaming(e.target.checked)}
                  className="rounded border-gray-600"
                />
                Stream responses (WebSocket)
              </label>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Sources Panel */}
      {sources.length > 0 && (
        <div className="hidden w-72 flex-shrink-0 xl:block">
          <GlassCard className="h-full overflow-y-auto p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              📎 Sources ({sources.length})
            </h3>
            <div className="mt-3 space-y-3">
              {sources.map((src: any, i: number) => (
                <div key={i} className="rounded-lg border border-white/[0.04] bg-white/[0.02] p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-medium text-violet-400">Source {i + 1}</span>
                    <span className="text-[10px] text-gray-500">
                      {(src.similarity_score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-gray-400">
                    {src.chunk_text}
                  </p>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
