/** 智能搜索页面 */

import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Card, Input, List, Tag, Typography, Space, Empty, Spin } from "antd";
import { SearchOutlined, EyeOutlined, FileTextOutlined } from "@ant-design/icons";
import { searchAPI } from "../../services/endpoints";
import type { SearchResult } from "../../types";

const { Text, Paragraph } = Typography;

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const [inputValue, setInputValue] = useState(query);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    if (query) {
      handleSearch(query);
    }
  }, [query]);

  const handleSearch = async (q: string, page = 1) => {
    setLoading(true);
    try {
      const res: any = await searchAPI.search({ q, page, page_size: 20 });
      setResults(res.data || []);
      setTotal(res.pagination?.total || 0);

      // 获取搜索建议
      const sugRes = await searchAPI.suggest(q);
      setSuggestions(sugRes.data || []);
    } catch {} finally {
      setLoading(false);
    }
  };

  const onSearch = (value: string) => {
    if (value.trim()) {
      setSearchParams({ q: value });
    }
  };

  const highlightText = (text: string) => {
    if (!query) return text;
    const regex = new RegExp(`(${query})`, "gi");
    const parts = text.split(regex);
    return parts.map((part, i) =>
      regex.test(part) ? (
        <span key={i} className="search-highlight">{part}</span>
      ) : (
        part
      )
    );
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <Card style={{ marginBottom: 24 }}>
        <Input.Search
          size="large"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onSearch={onSearch}
          placeholder="搜索知识库文档..."
          enterButton="搜索"
          prefix={<SearchOutlined />}
          loading={loading}
        />
        {suggestions.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <Text type="secondary">相关搜索：</Text>
            <Space wrap style={{ marginLeft: 8 }}>
              {suggestions.map((s, i) => (
                <Tag
                  key={i}
                  style={{ cursor: "pointer" }}
                  onClick={() => { setInputValue(s); onSearch(s); }}
                >
                  {s}
                </Tag>
              ))}
            </Space>
          </div>
        )}
      </Card>

      <Card title={`搜索结果 (${total})`}>
        {loading ? (
          <Spin tip="搜索中..." style={{ display: "block", textAlign: "center", padding: 40 }} />
        ) : results.length === 0 ? (
          <Empty description={query ? "未找到相关文档" : "请输入关键词搜索"} />
        ) : (
          <List
            dataSource={results}
            renderItem={(item) => (
              <List.Item
                style={{ cursor: "pointer" }}
                onClick={() => navigate(`/documents/${item.id}`)}
              >
                <List.Item.Meta
                  avatar={<FileTextOutlined style={{ fontSize: 22, color: "#1677ff" }} />}
                  title={
                    <Space>
                      <Text strong>{highlightText(item.title)}</Text>
                    </Space>
                  }
                  description={
                    <>
                      <Paragraph ellipsis={{ rows: 2 }} type="secondary">
                        {item.summary_text || "暂无摘要"}
                      </Paragraph>
                      <Space size="small">
                        <EyeOutlined /> <Text type="secondary">{item.view_count}</Text>
                        <Text type="secondary">{item.author_name}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>{item.created_at?.slice(0, 10)}</Text>
                        {item.tags?.map((t) => <Tag key={t} style={{ fontSize: 11 }}>{t}</Tag>)}
                      </Space>
                    </>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
