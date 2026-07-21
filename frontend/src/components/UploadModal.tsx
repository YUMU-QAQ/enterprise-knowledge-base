/** File upload component — drag & drop, multi-format support */

import { useState, useRef } from "react";
import { Modal, Upload, Button, Select, Form, message, Space, Typography } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import type { UploadFile, RcFile } from "antd/es/upload";
import { categoriesAPI } from "../services/endpoints";
import { useAuthStore } from "../stores/authStore";

const { Dragger } = Upload;
const { Text } = Typography;

const SUPPORTED_FORMATS =
  ".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md,.markdown";

interface Props {
  open: boolean;
  onClose: () => void;
  onUploaded: () => void;
}

export default function UploadModal({ open, onClose, onUploaded }: Props) {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [status, setStatus] = useState<string>("published");
  const [categories, setCategories] = useState<any[]>([]);
  const loadedRef = useRef(false);

  const loadCategories = async () => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    try {
      const res = await categoriesAPI.list();
      setCategories(res.data || []);
    } catch {}
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning("请选择文件");
      return;
    }

    setUploading(true);
    const token = useAuthStore.getState().token;

    let success = 0;
    let fail = 0;

    for (const file of fileList) {
      const formData = new FormData();
      formData.append("file", file as RcFile);
      if (categoryId) formData.append("category_id", String(categoryId));
      formData.append("status", status);

      try {
        const resp = await fetch("/api/v1/upload", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        });
        const data = await resp.json();
        if (resp.ok && data.code === 0) {
          success++;
        } else {
          fail++;
          message.error(`${file.name}: ${data?.detail?.message || data?.message || "上传失败"}`);
        }
      } catch {
        fail++;
        message.error(`${file.name}: 网络错误`);
      }
    }

    setUploading(false);

    if (success > 0) {
      message.success(`成功导入 ${success} 个文件${fail > 0 ? `，${fail} 个失败` : ""}`);
      onUploaded();
      onClose();
    }
  };

  return (
    <Modal
      title="📤 上传知识文件"
      open={open}
      onCancel={onClose}
      onOk={handleUpload}
      confirmLoading={uploading}
      okText="开始导入"
      width={640}
      destroyOnClose
      afterOpenChange={(visible) => {
        if (visible) {
          setFileList([]);
          loadedRef.current = false;
          loadCategories();
        }
      }}
    >
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Text type="secondary">
          支持 PDF、Word (.docx)、Excel (.xlsx/.xls)、CSV、TXT、Markdown 格式，单文件最大 50MB。文件内容将自动解析为知识库文档。
        </Text>

        <Dragger
          multiple
          accept={SUPPORTED_FORMATS}
          fileList={fileList}
          beforeUpload={(file) => {
            // Validate size
            if (file.size > 50 * 1024 * 1024) {
              message.error(`${file.name} 超过 50MB 限制`);
              return Upload.LIST_IGNORE;
            }
            // Validate extension
            const ext = file.name.split(".").pop()?.toLowerCase() || "";
            const allowed = ["pdf", "docx", "doc", "xlsx", "xls", "csv", "txt", "md", "markdown"];
            if (!allowed.includes(ext)) {
              message.error(`${file.name}: 不支持 .${ext} 格式`);
              return Upload.LIST_IGNORE;
            }
            setFileList((prev) => [...prev, file as UploadFile]);
            return false; // Prevent auto-upload
          }}
          onRemove={(file) => {
            setFileList((prev) => prev.filter((f) => f.uid !== file.uid));
          }}
          showUploadList={{ showPreviewIcon: false }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
          <p className="ant-upload-hint">支持单个或批量上传</p>
        </Dragger>

        <Space>
          <Form.Item label="分类" style={{ marginBottom: 0 }}>
            <Select
              allowClear
              placeholder="选择分类（可选）"
              style={{ width: 200 }}
              value={categoryId}
              onChange={setCategoryId}
              options={categories.map((c: any) => ({
                value: c.id,
                label: c.name,
              }))}
            />
          </Form.Item>
          <Form.Item label="状态" style={{ marginBottom: 0 }}>
            <Select
              value={status}
              onChange={setStatus}
              style={{ width: 120 }}
              options={[
                { value: "published", label: "发布" },
                { value: "draft", label: "草稿" },
              ]}
            />
          </Form.Item>
        </Space>
      </Space>
    </Modal>
  );
}
