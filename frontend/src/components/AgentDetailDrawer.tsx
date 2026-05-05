import { useEffect, useState } from "react";
import { Drawer, Spin, Card, Tag, Collapse, Typography, Space, Table, Statistic, Row, Col } from "antd";
import { api } from "../services/api";
import type { AgentDetail, AgentToolSchema, TokenRecord } from "../types";

const { Text, Paragraph } = Typography;

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

interface Props {
  agentId: string | null;
  onClose: () => void;
}

export default function AgentDetailDrawer({ agentId, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [selectedTool, setSelectedTool] = useState<AgentToolSchema | null>(null);
  const [tokenStats, setTokenStats] = useState<{
    total_records: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_cost: number;
    recent_runs: TokenRecord[];
  } | null>(null);

  useEffect(() => {
    if (agentId) {
      setLoading(true);
      Promise.all([
        api.getAgentDetail(agentId),
        api.getAgentTokenStats(agentId),
      ])
        .then(([detailRes, tokenRes]) => {
          setDetail(detailRes);
          setTokenStats(tokenRes);
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    } else {
      setDetail(null);
      setSelectedTool(null);
      setTokenStats(null);
    }
  }, [agentId]);

  return (
    <Drawer
      title={`Agent Detail: ${agentId}`}
      placement="right"
      width={800}
      onClose={onClose}
      open={!!agentId}
    >
      {loading ? (
        <Spin style={{ display: "block", margin: "50px auto" }} />
      ) : detail ? (
        <div style={{ display: "flex", gap: 16 }}>
          {/* Left Column */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
            <Card size="small" title="Status & Queue">
              <Text strong>Status:</Text> <Tag color={detail.state.status === "running" ? "green" : "default"}>{detail.state.status}</Tag><br />
              <Text strong>Task:</Text> {detail.state.task || "None"}<br />
              <Text strong>Last Active:</Text> {detail.state.last_active || "Never"}<br />
              {detail.state.queue_reason && (
                <div style={{ marginTop: 8, padding: 8, background: "rgba(250, 173, 20, 0.1)", border: "1px solid rgba(250, 173, 20, 0.2)", borderRadius: 4 }}>
                  <Text type="warning" strong>Queue Alert:</Text> {detail.state.queue_reason}
                </div>
              )}
            </Card>

            <Card size="small" title="Used Tools (Click for details)">
              <Space wrap>
                {detail.tools.map((t) => (
                  <Tag.CheckableTag
                    key={t.name}
                    checked={selectedTool?.name === t.name}
                    onChange={() => setSelectedTool(t)}
                    style={{ border: "1px solid #333" }}
                  >
                    {t.name}
                  </Tag.CheckableTag>
                ))}
              </Space>
              {selectedTool && (
                <div style={{ marginTop: 12, padding: 8, background: "#1f1f1f", borderRadius: 4, border: "1px solid #333" }}>
                  <Text strong>{selectedTool.name}</Text>
                  <Paragraph style={{ fontSize: 12, margin: "4px 0" }}>{selectedTool.description}</Paragraph>
                  <pre style={{ fontSize: 10, padding: 4, background: "#141414", color: "#a3e635", overflowX: "auto", border: "1px solid #333", borderRadius: 4 }}>
                    {JSON.stringify(selectedTool.input_schema, null, 2)}
                  </pre>
                </div>
              )}
            </Card>
          </div>

          {/* Right Column */}
          <div style={{ flex: 1.5, display: "flex", flexDirection: "column", gap: 16 }}>
            {tokenStats && tokenStats.total_records > 0 && (
              <Card size="small" title="Token Usage">
                <Row gutter={16} style={{ marginBottom: 12 }}>
                  <Col span={8}>
                    <Statistic title="Input" value={tokenStats.total_input_tokens} suffix="tok" valueStyle={{ fontSize: 16 }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="Output" value={tokenStats.total_output_tokens} suffix="tok" valueStyle={{ fontSize: 16 }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="Cost" value={tokenStats.total_cost} prefix="$" precision={2} valueStyle={{ fontSize: 16 }} />
                  </Col>
                </Row>
                <Table
                  dataSource={tokenStats.recent_runs.slice(0, 10)}
                  columns={[
                    { title: "Time", dataIndex: "timestamp", render: (v: string) => new Date(v).toLocaleString(), width: 120 },
                    { title: "In", dataIndex: "input_tokens", render: (v: number) => formatTokens(v), width: 60 },
                    { title: "Out", dataIndex: "output_tokens", render: (v: number) => formatTokens(v), width: 60 },
                    { title: "Cost", dataIndex: "cost", render: (v: number) => `$${v.toFixed(3)}`, width: 60 },
                    { title: "Tool Calls", dataIndex: "tool_calls", width: 60 },
                  ]}
                  size="small"
                  rowKey="run_id"
                  pagination={false}
                  scroll={{ y: 200 }}
                />
              </Card>
            )}
            <Card size="small" title="Logic Composition (Prompt Modules)">
              <Collapse size="small" defaultActiveKey={["IDENTITY.md"]}>
                {["IDENTITY.md", "AGENTS.md", "SOUL.md", "MEMORY.md", "TOOLS.md"].map((file) => {
                  const content = detail.components[file as keyof typeof detail.components];
                  if (!content || typeof content !== "string") return null;
                  return (
                    <Collapse.Panel header={file} key={file}>
                      <pre style={{ fontSize: 11, whiteSpace: "pre-wrap", margin: 0 }}>{content}</pre>
                    </Collapse.Panel>
                  );
                })}
                {detail.components.skills?.map((s) => (
                  <Collapse.Panel header={`SKILL: ${s.name}`} key={s.name}>
                    <pre style={{ fontSize: 11, whiteSpace: "pre-wrap", margin: 0 }}>{s.content}</pre>
                  </Collapse.Panel>
                ))}
              </Collapse>
            </Card>
          </div>
        </div>
      ) : null}
    </Drawer>
  );
}