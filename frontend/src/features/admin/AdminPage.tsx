/** 管理后台 */

import { useEffect, useState } from "react";
import { Card, Tabs, Descriptions, Button, Tag, message, Space, Statistic, Row, Col } from "antd";
import {
  SyncOutlined, ImportOutlined, DashboardOutlined,
} from "@ant-design/icons";
import { adminAPI, statsAPI } from "../../services/endpoints";

export default function AdminPage() {
  const [stats, setStats] = useState<any>({});
  const [integrations, setIntegrations] = useState<any>({ feishu: {}, dingtalk: {} });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsRes, intRes] = await Promise.all([
        statsAPI.overview(),
        adminAPI.integrations(),
      ]);
      setStats(statsRes.data || {});
      setIntegrations(intRes.data || { feishu: {}, dingtalk: {} });
    } catch {}
  };

  const syncFeishu = async () => {
    try {
      const res = await adminAPI.syncFeishuContacts();
      message.info(`飞书通讯录同步已下发 (task: ${res.data?.task_id})`);
    } catch {
      message.error("同步失败");
    }
  };

  const syncDingtalk = async () => {
    try {
      const res = await adminAPI.syncDingtalkContacts();
      message.info(`钉钉通讯录同步已下发 (task: ${res.data?.task_id})`);
    } catch {
      message.error("同步失败");
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <Tabs
        items={[
          {
            key: "overview",
            label: <span><DashboardOutlined /> 总览</span>,
            children: (
              <Card>
                <Row gutter={24}>
                  <Col span={8}>
                    <Statistic title="文档总数" value={stats.total_documents || 0} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="活跃用户" value={stats.total_users || 0} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="总阅读量" value={stats.total_views || 0} />
                  </Col>
                </Row>
              </Card>
            ),
          },
          {
            key: "feishu",
            label: "🕊️ 飞书集成",
            children: (
              <Card title="飞书配置">
                <Descriptions column={1}>
                  <Descriptions.Item label="状态">
                    <Tag color={integrations.feishu?.enabled ? "green" : "red"}>
                      {integrations.feishu?.enabled ? "已启用" : "未启用"}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="App ID">
                    {integrations.feishu?.app_id || "未配置"}
                  </Descriptions.Item>
                </Descriptions>
                <Space style={{ marginTop: 16 }}>
                  <Button icon={<SyncOutlined />} onClick={syncFeishu}>
                    同步通讯录
                  </Button>
                  <Button icon={<ImportOutlined />} onClick={async () => {
                    try {
                      await adminAPI.importFeishuDocs();
                      message.success("飞书文档导入已下发");
                    } catch { message.error("导入失败"); }
                  }}>
                    导入文档
                  </Button>
                </Space>
              </Card>
            ),
          },
          {
            key: "dingtalk",
            label: "📌 钉钉集成",
            children: (
              <Card title="钉钉配置">
                <Descriptions column={1}>
                  <Descriptions.Item label="状态">
                    <Tag color={integrations.dingtalk?.enabled ? "green" : "red"}>
                      {integrations.dingtalk?.enabled ? "已启用" : "未启用"}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="App Key">
                    {integrations.dingtalk?.app_key || "未配置"}
                  </Descriptions.Item>
                </Descriptions>
                <Space style={{ marginTop: 16 }}>
                  <Button icon={<SyncOutlined />} onClick={syncDingtalk}>
                    同步通讯录
                  </Button>
                  <Button icon={<ImportOutlined />} onClick={async () => {
                    try {
                      await adminAPI.importDingtalkDocs();
                      message.success("钉钉文档导入已下发");
                    } catch { message.error("导入失败"); }
                  }}>
                    导入文档
                  </Button>
                </Space>
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
