/** 知识库主页 — 分类浏览 + 文档列表 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Row, Col, Card, List, Tag, Typography, Space, Skeleton, Tree, Empty, Input } from "antd";
import {
  FileTextOutlined,
  EyeOutlined,
  LikeOutlined,
  FolderOutlined,
} from "@ant-design/icons";
import { documentsAPI, categoriesAPI } from "../../services/endpoints";
import type { DocumentItem, Category } from "../../types";

const { Text, Paragraph } = Typography;
const { Search } = Input;

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCat, setSelectedCat] = useState<number | undefined>();
  const navigate = useNavigate();

  useEffect(() => {
    loadCategories();
    loadDocuments();
  }, [selectedCat]);

  const loadCategories = async () => {
    try {
      const res = await categoriesAPI.list();
      setCategories(res.data || []);
    } catch {}
  };

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page: 1, page_size: 20 };
      if (selectedCat) params.category_id = selectedCat;
      const res = await documentsAPI.list(params);
      setDocuments(res.data || []);
    } catch {} finally {
      setLoading(false);
    }
  };

  const buildTreeData = (cats: Category[]): any[] =>
    cats.map((cat) => ({
      key: cat.id,
      title: (
        <Space>
          <FolderOutlined />
          <span>{cat.name}</span>
          <Tag>{cat.document_count}</Tag>
        </Space>
      ),
      children: cat.children ? buildTreeData(cat.children) : undefined,
    }));

  return (
    <Row gutter={24}>
      {/* 左侧分类树 */}
      <Col xs={24} md={6}>
        <Card title="📂 文档分类" size="small" style={{ position: "sticky", top: 24 }}>
          <div
            style={{
              padding: "4px 0",
              marginBottom: 8,
              cursor: "pointer",
              color: selectedCat === undefined ? "#1677ff" : "inherit",
              fontWeight: selectedCat === undefined ? 600 : 400,
            }}
            onClick={() => setSelectedCat(undefined)}
          >
            全部文档
          </div>
          <Tree
            treeData={buildTreeData(categories)}
            showIcon={false}
            blockNode
            selectedKeys={selectedCat ? [selectedCat] : []}
            onSelect={(keys) => {
              if (keys.length > 0) setSelectedCat(keys[0] as number);
              else setSelectedCat(undefined);
            }}
          />
        </Card>
      </Col>

      {/* 右侧文档列表 */}
      <Col xs={24} md={18}>
        <Card
          title="📄 文档列表"
          extra={
            <Search placeholder="搜索文档..." onSearch={(q) => navigate(`/search?q=${q}`)} style={{ width: 250 }} />
          }
        >
          {loading ? (
            <Skeleton active paragraph={{ rows: 5 }} />
          ) : documents.length === 0 ? (
            <Empty description="暂无文档" />
          ) : (
            <List
              dataSource={documents}
              renderItem={(doc) => (
                <List.Item
                  extra={
                    <Space>
                      <Text type="secondary"><EyeOutlined /> {doc.view_count}</Text>
                      <Text type="secondary"><LikeOutlined /> {doc.like_count}</Text>
                    </Space>
                  }
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/documents/${doc.id}`)}
                >
                  <List.Item.Meta
                    avatar={<FileTextOutlined style={{ fontSize: 24, color: "#1677ff" }} />}
                    title={
                      <Space>
                        <Text strong>{doc.title}</Text>
                        {doc.tags?.map((t) => (
                          <Tag key={t.id} color={t.color}>{t.name}</Tag>
                        ))}
                      </Space>
                    }
                    description={
                      <>
                        <Paragraph ellipsis={{ rows: 2 }} type="secondary" style={{ marginBottom: 4 }}>
                          {doc.summary_text || "暂无摘要"}
                        </Paragraph>
                        <Space size="small">
                          <Text type="secondary" style={{ fontSize: 12 }}>{doc.author_name}</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>{doc.updated_at?.slice(0, 10)}</Text>
                          {doc.category_name && (
                            <Tag style={{ fontSize: 11 }}>{doc.category_name}</Tag>
                          )}
                        </Space>
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      </Col>
    </Row>
  );
}
