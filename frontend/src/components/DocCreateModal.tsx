/** 创建/编辑文档对话框 */

import { useState, useEffect } from "react";
import { Modal, Form, Input, Select, message } from "antd";
import { documentsAPI, categoriesAPI, tagsAPI } from "../services/endpoints";

// Minimal Markdown editor
function MarkdownEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <Input.TextArea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      rows={16}
      placeholder={"支持 Markdown 格式\n\n# 一级标题\n## 二级标题\n\n正文内容...\n\n```python\nprint('代码块')\n```"}
      style={{ fontFamily: "monospace", fontSize: 14, lineHeight: 1.6 }}
    />
  );
}

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function DocCreateModal({ open, onClose, onCreated }: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState<any[]>([]);

  useEffect(() => {
    if (open) {
      form.resetFields();
      loadCategories();
    }
  }, [open]);

  const loadCategories = async () => {
    try {
      const res = await categoriesAPI.list();
      setCategories(res.data || []);
    } catch {}
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      await documentsAPI.create({
        title: values.title,
        content: values.content_md,
        content_md: values.content_md,
        format: "markdown",
        status: values.status || "published",
        category_id: values.category_id || null,
        tag_ids: [],
      });
      message.success("文档创建成功");
      onCreated();
      onClose();
    } catch (err: any) {
      message.error(err?.message || "创建失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="📝 新建文档"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={loading}
      width={800}
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item
          name="title"
          label="文档标题"
          rules={[{ required: true, message: "请输入标题" }]}
        >
          <Input placeholder="输入文档标题" />
        </Form.Item>

        <Form.Item name="category_id" label="分类">
          <Select
            allowClear
            placeholder="选择分类（可选）"
            options={categories.map((c: any) => ({
              value: c.id,
              label: c.name,
            }))}
          />
        </Form.Item>

        <Form.Item name="status" label="状态" initialValue="published">
          <Select
            options={[
              { value: "published", label: "发布" },
              { value: "draft", label: "草稿" },
            ]}
          />
        </Form.Item>

        <Form.Item
          name="content_md"
          label="正文内容（Markdown）"
          rules={[{ required: true, message: "请输入内容" }]}
        >
          <MarkdownEditor value="" onChange={() => {}} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
