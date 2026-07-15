/** 应用主布局 — 侧边导航 + 顶部 header + 内容区 */

import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Button, Avatar, Dropdown } from "antd";
import {
  BookOutlined,
  SearchOutlined,
  StarOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../stores/authStore";

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: "/knowledge", icon: <BookOutlined />, label: "知识库" },
  { key: "/search", icon: <SearchOutlined />, label: "智能搜索" },
  { key: "/recommend", icon: <StarOutlined />, label: "推荐" },
  { key: "/admin", icon: <SettingOutlined />, label: "管理后台" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const selectedKey = "/" + location.pathname.split("/")[1];

  const userMenu = {
    items: [
      { key: "profile", icon: <UserOutlined />, label: "个人信息" },
      { type: "divider" as const },
      { key: "logout", icon: <LogoutOutlined />, label: "退出登录", danger: true },
    ],
    onClick: ({ key }: { key: string }) => {
      if (key === "logout") {
        logout();
        navigate("/login");
      }
    },
  };

  return (
    <Layout style={{ height: "100vh" }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="light"
        style={{ borderRight: "1px solid #f0f0f0" }}
      >
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: collapsed ? 14 : 18,
            color: "#1677ff",
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          {collapsed ? "📚" : "📚 企业知识库"}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Dropdown menu={userMenu} placement="bottomRight">
            <div style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
              <Avatar icon={<UserOutlined />} src={user?.avatar_url} />
              <span>{user?.display_name || user?.username}</span>
            </div>
          </Dropdown>
        </Header>

        <Content
          style={{
            padding: 24,
            overflow: "auto",
            background: "#f5f5f5",
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
