/** 文档详情页 */

import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Typography, Tag, Space, Button, Divider, List, Skeleton, message, Tooltip
} from "antd";
import {
  EyeOutlined, LikeOutlined, ClockCircleOutlined, ArrowLeftOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { documentsAPI, recommendAPI, summarizeAPI } from "../../services/endpoints";
import type { DocumentDetail } from "../../types";

const { Title, Paragraph, Text } = Typography;

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [similar, setSimilar] = useState<any[]>([]);
  const [comments, setComments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    if (id) loadDocument(Number(id));
    window.scrollTo(0, 0);
  }, [id]);

  const loadDocument = async (docId: number) => {
    setLoading(true);
    try {
      const [docRes, simRes, comRes] = await Promise.all([
        documentsAPI.get(docId),
        recommendAPI.similar(docId, 5),
        documentsAPI.comments(docId, { page: 1, page_size: 50 }),
      ]);
      setDoc(docRes.data);
      setSimilar(simRes.data || []);
      setComments(comRes.data || []);
    } catch {
      message.error("文档不存在或无权访问");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!doc) return;
    try {
      await summarizeAPI.generate(doc.id);
      message.success("摘要生成任务已下发，请稍后刷新查看");
    } catch {
      message.error("摘要生成失败");
    }
  };

  if (loading) return <Skeleton active paragraph={{ rows: 10 }} />;
  if (!doc) return null;

  return (
    <div style={{ maxWidth: 960, margin: "0 auto" }}>
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate(-1)}
        style={{ marginBottom: 16 }}
      >
        返回
      </Button>

      <Card>
        <Title level={3}>{doc.title}</Title>

        <Space style={{ marginBottom: 16 }} wrap>
          <Text type="secondary"><EyeOutlined /> {doc.view_count} 次阅读</Text>
          <Text type="secondary"><LikeOutlined /> {doc.like_count} 次点赞</Text>
          <Text type="secondary"><ClockCircleOutlined /> {doc.updated_at?.slice(0, 10)}</Text>
          {doc.author_name && <Tag>{doc.author_name}</Tag>}
          {doc.category_name && <Tag color="blue">{doc.category_name}</Tag>}
          {doc.tags?.map((t: any) => (
            <Tag key={t.id} color={t.color}>{t.name}</Tag>
          ))}
        </Space>

        <Space style={{ marginBottom: 16 }}>
          <Tooltip title="AI 摘要">
            <Button icon={<RobotOutlined />} size="small" onClick={handleGenerateSummary}>
              {doc.summary_text ? "重新生成摘要" : "生成摘要"}
            </Button>
          </Tooltip>
        </Space>

        {doc.summary_text && (
          <Card size="small" style={{ background: "#f0f5ff", marginBottom: 20, border: "1px solid #d6e4ff" }}>
            <Text type="secondary">🤖 AI 摘要：</Text>
            <Paragraph style={{ marginTop: 8, marginBottom: 0 }}>{doc.summary_text}</Paragraph>
          </Card>
        )}

        <Divider />

        <div className="doc-content" style={{ lineHeight: 1.8, fontSize: 15 }}>
          {doc.content_md ? (
            <Paragraph style={{ whiteSpace: "pre-wrap" }}>{doc.content_md}</Paragraph>
          ) : doc.content ? (
            <div dangerouslySetInnerHTML={{ __html: doc.content }} />
          ) : (
            <Text type="secondary">文档内容为空</Text>
          )}
        </div>
      </Card>

      {/* 相似推荐 */}
      {similar.length > 0 && (
        <Card title="📎 相关推荐" size="small" style={{ marginTop: 16 }}>
          <List
            size="small"
            dataSource={similar}
            renderItem={(item: any) => (
              <List.Item
                style={{ cursor: "pointer" }}
                onClick={() => navigate(`/documents/${item.id}`)}
              >
                <List.Item.Meta
                  title={item.title}
                  description={item.summary_text?.slice(0, 80) || ""}
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 评论区 */}
      <Card title="💬 评论" size="small" style={{ marginTop: 16 }}>
        {comments.length === 0 ? (
          <Text type="secondary">暂无评论</Text>
        ) : (
          <List
            size="small"
            dataSource={comments}
            renderItem={(c: any) => (
              <List.Item>
                <List.Item.Meta
                  avatar={c.user_name?.[0]}
                  title={c.user_name}
                  description={c.content}
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
