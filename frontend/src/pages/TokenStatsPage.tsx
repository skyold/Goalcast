import { useEffect, useState } from "react";
import { Card, Table, Tag, Row, Col, Statistic, Typography, DatePicker, Space, Select } from "antd";
import { DollarOutlined, LineChartOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "../services/api";
import type { TokenSummary, TokenRecord } from "../types";

const { Text } = Typography;
const { RangePicker } = DatePicker;

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function TokenStatsPage() {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<TokenSummary | null>(null);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [agentFilter, setAgentFilter] = useState<string | undefined>(undefined);
  const [records, setRecords] = useState<TokenRecord[]>([]);

  const fetchData = () => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (dateRange) {
      params.start_date = dateRange[0].format("YYYY-MM-DD");
      params.end_date = dateRange[1].format("YYYY-MM-DD");
    }
    if (agentFilter) {
      params.agent_id = agentFilter;
    }

    Promise.all([
      api.getTokenSummary(params),
      api.getTokenRecords({ ...params, limit: 200 }),
    ])
      .then(([summaryRes, recordsRes]) => {
        setSummary(summaryRes);
        setRecords(recordsRes.items);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [dateRange, agentFilter]);

  const agentOptions = summary
    ? summary.by_agent.map((a) => ({ value: a.agent_id, label: a.agent_id }))
    : [];

  const dayColumns = [
    {
      title: "Date",
      dataIndex: "date",
      key: "date",
      render: (v: string) => <Text strong>{v}</Text>,
      width: 120,
    },
    {
      title: "Input Tokens",
      dataIndex: "input_tokens",
      key: "input_tokens",
      render: (v: number) => formatTokens(v),
    },
    {
      title: "Output Tokens",
      dataIndex: "output_tokens",
      key: "output_tokens",
      render: (v: number) => formatTokens(v),
    },
    {
      title: "Total",
      dataIndex: "total_tokens",
      key: "total_tokens",
      render: (v: number) => formatTokens(v),
    },
    {
      title: "Cost",
      dataIndex: "cost",
      key: "cost",
      render: (v: number) => (
        <Tag color="purple">${v.toFixed(2)}</Tag>
      ),
    },
    {
      title: "Runs",
      dataIndex: "run_count",
      key: "run_count",
    },
  ];

  const agentColumns = [
    {
      title: "Agent",
      dataIndex: "agent_id",
      key: "agent_id",
      render: (v: string) => <Text strong style={{ color: "#60a5fa" }}>{v}</Text>,
    },
    {
      title: "Input",
      dataIndex: "input_tokens",
      key: "input_tokens",
      render: (v: number) => formatTokens(v),
    },
    {
      title: "Output",
      dataIndex: "output_tokens",
      key: "output_tokens",
      render: (v: number) => formatTokens(v),
    },
    {
      title: "Total Tokens",
      dataIndex: "total_tokens",
      key: "total_tokens",
      render: (v: number) => formatTokens(v),
    },
    {
      title: "Cost",
      dataIndex: "cost",
      key: "cost",
      render: (v: number) => <Tag color="purple">${v.toFixed(2)}</Tag>,
      sorter: (a: any, b: any) => a.cost - b.cost,
    },
    {
      title: "Runs",
      dataIndex: "run_count",
      key: "run_count",
    },
  ];

  const recordColumns = [
    {
      title: "Time",
      dataIndex: "timestamp",
      key: "timestamp",
      render: (v: string) => new Date(v).toLocaleString(),
      width: 160,
    },
    {
      title: "Agent",
      dataIndex: "agent_id",
      key: "agent_id",
      render: (v: string) => <Tag color="blue">{v}</Tag>,
      width: 140,
    },
    {
      title: "Hypothesis",
      dataIndex: "hypothesis_id",
      key: "hypothesis_id",
      render: (v: string) => v ? <Tag>{v}</Tag> : "—",
      width: 200,
    },
    {
      title: "Model",
      dataIndex: "model",
      key: "model",
      render: (v: string) => <Text type="secondary" style={{ fontSize: 12 }}>{v}</Text>,
      width: 140,
    },
    {
      title: "Input",
      dataIndex: "input_tokens",
      key: "input_tokens",
      render: (v: number) => formatTokens(v),
    },
    {
      title: "Output",
      dataIndex: "output_tokens",
      key: "output_tokens",
      render: (v: number) => formatTokens(v),
    },
    {
      title: "Cache (Create/Read)",
      key: "cache",
      render: (_: any, r: TokenRecord) => (
        <Text type="secondary">{r.cache_creation_tokens > 0 || r.cache_read_tokens > 0 ? `${formatTokens(r.cache_creation_tokens)} / ${formatTokens(r.cache_read_tokens)}` : "—"}</Text>
      ),
    },
    {
      title: "Rounds",
      dataIndex: "rounds",
      key: "rounds",
    },
    {
      title: "Tool Calls",
      dataIndex: "tool_calls",
      key: "tool_calls",
    },
    {
      title: "Cost",
      dataIndex: "cost",
      key: "cost",
      render: (v: number) => <Tag color="purple">${v.toFixed(3)}</Tag>,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (v: string) => (
        <Tag color={v === "success" ? "green" : v === "error" ? "red" : "default"}>{v}</Tag>
      ),
    },
  ];

  return (
    <div>
      {/* Summary Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small" loading={loading}>
            <Statistic
              title="Total Tokens"
              value={summary?.total_tokens ?? 0}
              suffix={<Text type="secondary" style={{ fontSize: 14 }}>tokens</Text>}
              valueStyle={{ color: "#a855f7" }}
              formatter={(v) => formatTokens(v as number)}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" loading={loading}>
            <Statistic
              title="Input Tokens"
              value={summary?.total_input_tokens ?? 0}
              prefix={<LineChartOutlined />}
              valueStyle={{ color: "#60a5fa" }}
              formatter={(v) => formatTokens(v as number)}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" loading={loading}>
            <Statistic
              title="Output Tokens"
              value={summary?.total_output_tokens ?? 0}
              valueStyle={{ color: "#4ade80" }}
              formatter={(v) => formatTokens(v as number)}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" loading={loading}>
            <Statistic
              title="Estimated Cost"
              value={summary?.total_cost ?? 0}
              prefix={<DollarOutlined />}
              precision={2}
              valueStyle={{ color: "#fbbf24" }}
              suffix="USD"
            />
          </Card>
        </Col>
      </Row>

      <Row style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <RangePicker
              value={dateRange}
              onChange={(dates) => setDateRange(dates as any)}
              allowClear
            />
            <Select
              allowClear
              placeholder="Filter by agent"
              options={agentOptions}
              style={{ width: 200 }}
              value={agentFilter}
              onChange={setAgentFilter}
            />
          </Space>
        </Col>
      </Row>

      {/* By Agent */}
      <Card size="small" title="Token Usage by Agent" style={{ marginBottom: 16 }} loading={loading}>
        <Table
          dataSource={summary?.by_agent ?? []}
          columns={agentColumns}
          rowKey="agent_id"
          size="small"
          pagination={false}
          locale={{ emptyText: "No agent data yet" }}
        />
      </Card>

      {/* By Day */}
      <Card size="small" title="Daily Token Usage" style={{ marginBottom: 16 }} loading={loading}>
        <Table
          dataSource={summary?.by_day ?? []}
          columns={dayColumns}
          rowKey="date"
          size="small"
          pagination={false}
          locale={{ emptyText: "No daily data yet" }}
        />
      </Card>

      {/* Recent Records */}
      <Card size="small" title="Recent Token Records" loading={loading}>
        <Table
          dataSource={records}
          columns={recordColumns}
          rowKey="run_id"
          size="small"
          pagination={{ pageSize: 20 }}
          locale={{ emptyText: "No records yet" }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
}
