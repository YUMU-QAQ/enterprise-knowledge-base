/** 智能推荐页面 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, List, Tag, Typography, Space, Spin, Empty, Tabs } from "antd";
import { FireOutlined, BulbOutlined, EyeOutlined, FileTextOutlined } from "@ant-design/icons";
import { recommendAPI } from "../../services/endpoints";

const { Text, Paragraph } = Typography;

export default function RecommendPage() {
  const [personal, setPersonal] = useState<any[]>([]);
  const [hot, setHot] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadRecommendations();
  }, []);

  const loadRecommendations = async () => {
    setLoading(true);
    try {
      const [perRes, hotRes] = await Promise.all([
        recommendAPI.personal(10),
        recommendAPI.hot(10),
      ]);
      setPersonal(perRes.data || []);
      setHot(hotRes.data || []);
    } catch {} finally {
      setLoading(false);
    }
  };

  const renderList = (items: any[]) => (
    <List
      dataSource={items}
      renderItem={(item) => (
        <List.Item
          style={{ cursor: "pointer" }}
          onClick={() => navigate(`/documents/${item.id}`)}
        >
          <List.Item.Meta
            avatar={<FileTextOutlined style={{ fontSize: 22, color: "#1677ff" }} />}
            title={item.title}
            description={
              <>
                <Paragraph ellipsis={{ rows: 1 }} type="secondary">
                  {item.summary_text || "暂无摘要"}
                </Paragraph>
                <Space size="small">
                  <EyeOutlined /> <Text type="secondary">{item.view_count}</Text>
                  {item.reason && <Tag color="green" style={{ fontSize: 11 }}>{item.reason}</Tag>}
                </Space>
              </>
            }
          />
        </List.Item>
      )}
    />
  );

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <Card style={{ marginBottom: 24 }}>
        <Tabs
          items={[
            {
              key: "personal",
              label: <span><BulbOutlined /> 为你推荐</span>,
              children: loading ? <Spin style={{ display: "block", textAlign: "center", padding: 40 }} /> :
                personal.length === 0 ? <Empty description="阅读更多文档以获取个性化推荐" /> :
                renderList(personal),
            },
            {
              key: "hot",
              label: <span><FireOutlined /> 热门文档</span>,
              children: loading ? <Spin style={{ display: "block", textAlign: "center", padding: 40 }} /> :
                renderList(hot),
            },
          ]}
        />
      </Card>
    </div>
  );
}
