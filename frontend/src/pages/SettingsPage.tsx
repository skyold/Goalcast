import { Typography, Card, Form, Input, InputNumber, Alert, Tag, Space } from "antd";

export default function SettingsPage() {
  return (
    <div style={{ padding: 24, maxWidth: 900 }}>
      <Typography.Title level={3}>⚙️ 设置</Typography.Title>

      <Card title="🔌 OddAlerts API" style={{ marginBottom: 14 }}>
        <Form layout="vertical">
          <Form.Item label="API Token" extra="从 OddAlerts 控制台获取，单点配额 300 req/min">
            <Input.Password placeholder="oa_xxxxxxxxxxxxxxxx" />
          </Form.Item>
          <Form.Item label="速率上限 (req/min)">
            <InputNumber defaultValue={280} min={1} max={300} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="🎯 分析参数" style={{ marginBottom: 14 }}>
        <Form layout="vertical">
          <Form.Item label="概率混合权重 (Poisson / OddAlerts trends / 市场, 和=1)">
            <Space>
              <InputNumber defaultValue={0.5} min={0} max={1} step={0.1} />
              <InputNumber defaultValue={0.4} min={0} max={1} step={0.1} />
              <InputNumber defaultValue={0.1} min={0} max={1} step={0.1} />
            </Space>
          </Form.Item>
          <Form.Item label="最低 EV 阈值 (%)">
            <InputNumber defaultValue={2.0} min={0} step={0.5} />
          </Form.Item>
          <Form.Item label="最低置信度 (星)">
            <InputNumber defaultValue={3} min={0} max={5} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="💰 资金 / Kelly" style={{ marginBottom: 14 }}>
        <Form layout="vertical">
          <Form.Item label="基准 Bankroll (u)">
            <InputNumber defaultValue={100} min={1} />
          </Form.Item>
          <Form.Item label="Kelly 分数">
            <InputNumber defaultValue={0.25} min={0.05} max={1} step={0.05} />
          </Form.Item>
          <Form.Item label="单注上限 (u)">
            <InputNumber defaultValue={3.0} min={0.1} step={0.5} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="⚠ Legacy 数据源 (只读)" style={{ marginBottom: 14 }}>
        <Alert type="warning" showIcon
               message="以下数据源已在 2026-05-14 架构升级中删除，不可重新启用。" />
        <div style={{ marginTop: 12 }}>
          <Tag>FootyStats</Tag><Tag>Sportmonks</Tag><Tag>Understat</Tag>
          <span style={{ marginLeft: 10, color: "#555d72" }}>已删除 · 已删除 · 已删除</span>
        </div>
      </Card>
    </div>
  );
}
