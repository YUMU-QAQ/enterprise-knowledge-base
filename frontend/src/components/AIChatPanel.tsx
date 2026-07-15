/** 浮动 AI 对话面板 */

import { useState, useRef, useEffect } from "react";
import { FloatButton, Input, Typography, Tag, Space, Spin } from "antd";
import { RobotOutlined, SendOutlined, CloseOutlined } from "@ant-design/icons";
import { chatAPI } from "../services/endpoints";

const { Text } = Typography;

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { id: number; title: string; score: number }[];
}

export default function AIChatPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await chatAPI.ask(input);
      const reader = response.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "",
        sources: [],
      };
      setMessages((prev) => [...prev, assistantMsg]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n").filter((l) => l.startsWith("data: "));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "answer") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsg.id ? { ...m, content: m.content + data.content } : m
                )
              );
            } else if (data.type === "sources") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsg.id ? { ...m, sources: data.docs } : m
                )
              );
            }
          } catch {}
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), role: "assistant", content: "抱歉，请求失败，请稍后重试。" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-chat-panel">
      {open ? (
        <div className="ai-chat-window">
          {/* Header */}
          <div
            style={{
              padding: "12px 16px",
              background: "#1677ff",
              color: "#fff",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Space>
              <RobotOutlined />
              <span style={{ fontWeight: 600 }}>AI 助手</span>
            </Space>
            <CloseOutlined
              style={{ cursor: "pointer" }}
              onClick={() => setOpen(false)}
            />
          </div>

          {/* Messages */}
          <div
            ref={listRef}
            style={{ flex: 1, overflow: "auto", padding: 16 }}
          >
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  marginBottom: 16,
                  textAlign: msg.role === "user" ? "right" : "left",
                }}
              >
                <div
                  style={{
                    display: "inline-block",
                    maxWidth: "85%",
                    padding: "8px 14px",
                    borderRadius: 12,
                    background: msg.role === "user" ? "#e6f4ff" : "#f5f5f5",
                    textAlign: "left",
                  }}
                >
                  <Text>{msg.content}</Text>
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        参考来源：
                      </Text>
                      {msg.sources.map((s) => (
                        <Tag key={s.id} style={{ marginTop: 4, fontSize: 11 }}>
                          {s.title}
                        </Tag>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ textAlign: "center", padding: 8 }}>
                <Spin size="small" /> 思考中...
              </div>
            )}
          </div>

          {/* Input */}
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
          className="ai-chat-float-btn"
          icon={<RobotOutlined />}
          type="primary"
          onClick={() => setOpen(true)}
          tooltip="AI 助手"
        />
      )}
    </div>
  );
}
