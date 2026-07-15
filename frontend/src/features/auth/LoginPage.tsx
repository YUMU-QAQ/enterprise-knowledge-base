/** 登录页面 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Input, Button, Card, Typography, Divider, message, Space, Tabs } from "antd";
import { UserOutlined, LockOutlined, WechatOutlined } from "@ant-design/icons";
import { authAPI } from "../../services/endpoints";
import { useAuthStore } from "../../stores/authStore";

const { Title, Text } = Typography;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await authAPI.login(values.username, values.password);
      setAuth(res.data.access_token, res.data.refresh_token, res.data.user);
      message.success(`欢迎回来，${res.data.user.display_name}`);
      navigate("/knowledge");
    } catch (err: any) {
      message.error(err?.message || "登录失败");
    } finally {
      setLoading(false);
    }
  };

  const handleFeishuLogin = async () => {
    try {
      const res = await authAPI.feishuLoginUrl();
      window.location.href = res.data.url;
    } catch {
      message.info("飞书登录暂未配置");
    }
  };

  const handleDingtalkLogin = async () => {
    try {
      const res = await authAPI.dingtalkLoginUrl();
      window.location.href = res.data.url;
    } catch {
      message.info("钉钉登录暂未配置");
    }
  };

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      }}
    >
      <Card style={{ width: 420, borderRadius: 12, boxShadow: "0 8px 32px rgba(0,0,0,0.15)" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <Title level={3} style={{ marginBottom: 4 }}>
            📚 企业知识库
          </Title>
          <Text type="secondary">智能知识管理平台</Text>
        </div>

        <Tabs
          centered
          items={[
            {
              key: "password",
              label: "账号登录",
              children: (
                <Form onFinish={handleLogin} size="large" style={{ marginTop: 16 }}>
                  <Form.Item name="username" rules={[{ required: true, message: "请输入用户名" }]}>
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading} block>
                      登录
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: "register",
              label: "注册",
              children: (
                <Form onFinish={async (v) => {
                  try {
                    await authAPI.register(v);
                    message.success("注册成功，请登录");
                  } catch (err: any) {
                    message.error(err?.message || "注册失败");
                  }
                }} size="large" style={{ marginTop: 16 }}>
                  <Form.Item name="username" rules={[{ required: true }]}>
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item name="display_name" rules={[{ required: true, message: "请输入显示名称" }]}>
                    <Input placeholder="显示名称" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, min: 6 }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="密码（至少6位）" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" block>
                      注册
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />

        <Divider plain>
          <Text type="secondary">其他方式登录</Text>
        </Divider>

        <Space style={{ width: "100%", justifyContent: "center" }}>
          <Button icon={<WechatOutlined style={{ color: "#00c78c" }} />} onClick={handleFeishuLogin}>
            飞书
          </Button>
          <Button
            icon={<span style={{ color: "#1677ff", fontWeight: "bold" }}>钉</span>}
            onClick={handleDingtalkLogin}
          >
            钉钉
          </Button>
        </Space>
      </Card>
    </div>
  );
}
