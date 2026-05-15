import { Table } from "antd";
interface Props { h2h?: any[]; }
export default function H2HTable({ h2h = [] }: Props) {
  return (
    <Table
      size="small" pagination={false}
      dataSource={h2h.map((r, i) => ({ key: i, ...r }))}
      columns={[
        { title: "日期", dataIndex: "date" },
        { title: "主场", dataIndex: "home" },
        { title: "比分", dataIndex: "score" },
        { title: "客场", dataIndex: "away" },
      ]}
      locale={{ emptyText: "无 H2H 数据" }}
    />
  );
}
