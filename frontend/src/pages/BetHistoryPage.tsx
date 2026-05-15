import { Typography, Alert, Table } from "antd";

export default function BetHistoryPage() {
  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>📒 下注记录</Typography.Title>
      <Alert type="info" message="下注记录持久化将在后续版本接入；当前为占位。" />
      <Table
        size="small" style={{ marginTop: 12 }} dataSource={[]} rowKey="id"
        locale={{ emptyText: "暂无下注" }}
        columns={[
          { title: "日期", dataIndex: "date" },
          { title: "比赛", dataIndex: "match" },
          { title: "市场", dataIndex: "market" },
          { title: "赔率", dataIndex: "odds" },
          { title: "盈亏", dataIndex: "pnl" },
        ]}
      />
    </div>
  );
}
