/** Floating AI Chat Panel — SSE streaming */

import { useState, useRef, useEffect } from "react";
import { FloatButton, Input, Typography, Tag, Space, Spin } from "antd";
import { RobotOutlined, SendOutlined, CloseOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface Message {
  id: string;
  role: "user" | "assistant" | "thinking" | "error";
  content: string;
  sources?: { id: number; title: string; score: number }[];
}

export default function AIChatPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, statusText]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setStatusText("思考中...");

    const assistantId = (Date.now() + 1).toString();
    let assistantContent = "";
    let sources: any[] = [];

    try {
      const token = localStorage.getItem("auth-storage");
      const parsed = token ? JSON.parse(token) : null;
      const jwt = parsed?.state?.token || "";

      const response = await fetch("/api/v1/chat/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${jwt}`,
        },
        body: JSON.stringify({ question: input }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err?.detail?.message || err?.message || "Request failed");
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            switch (data.type) {
              case "thinking":
                setStatusText(data.content || "处理中...");
                break;
              case "sources":
                sources = data.docs || [];
                break;
              case "answer":
                assistantContent += data.content || "";
                setMessages((prev) => {
                  const updated = [...prev];
                  const existing = updated.find((m) => m.id === assistantId);
                  if (existing) {
                    existing.content = assistantContent;
                    existing.sources = sources;
                  } else {
                    updated.push({ id: assistantId, role: "assistant", content: assistantContent, sources });
                  }
                  return updated;
                });
                break;
              case "error":
                setMessages((prev) => [...prev, { id: assistantId, role: "error", content: data.content || "AI 服务出错" }]);
                break;
            }
          } catch {}
        }
      }

      if (!assistantContent && sources.length === 0) {
        // No answer was generated — the last event might have been an error we didn't catch
        const lastMsg = messages.find((m) => m.id === assistantId);
        if (!lastMsg) {
          setMessages((prev) => [
            ...prev,
            { id: assistantId, role: "assistant", content: "知识库中暂未找到相关内容。请先上传一些知识文档。" },
          ]);
        }
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "error", content: err?.message || "抱歉，请求失败，请稍后重试。" },
      ]);
    } finally {
      setLoading(false);
      setStatusText("");
    }
  };

  return (
    <div className="ai-chat-panel">
      {open ? (
        <div className="ai-chat-window">
          <div style={{ padding: "12px 16px", background: "#1677ff", color: "#fff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Space>
              <RobotOutlined />
              <span style={{ fontWeight: 600 }}>AI 助手</span>
            </Space>
            <CloseOutlined style={{ cursor: "pointer" }} onClick={() => setOpen(false)} />
          </div>

          <div ref={listRef} style={{ flex: 1, overflow: "auto", padding: 16 }}>
            {messages.map((msg) => (
              <div key={msg.id} style={{ marginBottom: 16, textAlign: msg.role === "user" ? "right" : "left" }}>
                <div style={{
                  display: "inline-block", maxWidth: "85%", padding: "8px 14px", borderRadius: 12,
                  background: msg.role === "user" ? "#e6f4ff" : msg.role === "error" ? "#fff2f0" : "#f5f5f5",
                  textAlign: "left",
                }}>
                  {msg.role === "error" && <Text type="danger" style={{ fontSize: 12 }}>⚠️ </Text>}
                  <Text style={{ whiteSpace: "pre-wrap" }}>{msg.content}</Text>
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: 8, borderTop: "1px solid #e8e8e8", paddingTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>参考来源：</Text>
                      <div style={{ marginTop: 4 }}>
                        {msg.sources.map((s) => (
                          <Tag key={s.id} style={{ marginTop: 2, fontSize: 10 }}>{s.title}</Tag>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ textAlign: "center", padding: 8 }}>
                <Spin size="small" /> {statusText || "思考中..."}
              </div>
            )}
          </div>

          <div style={{ padding: "8px 16px", borderTop: "1px solid #f0f0f0" }}>
            <Input.Search
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onSearch={handleSend}
              placeholder="输入问题，基于知识库回答..."
              enterButton={<SendOutlined />}
              loading={loading}
            />
          </div>
        </div>
      ) : (
        <FloatButton
          icon={<RobotOutlined />}
          type="primary"
          onClick={() => setOpen(true)}
          tooltip="AI 助手"
        />
      )}
    </div>
  );
}
