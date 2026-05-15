import { Table } from "antd";
import type { OddsHistory } from "../types/browse";

interface Props { history?: OddsHistory; }

export default function MarketDepthTable({ history }: Props) {
  if (!history) return <div style={{ color: "#555d72" }}>无赔率数据</div>;
  const market = history.markets?.ft_result || {};
  const rows = Object.entries(market).map(([book, lines]) => ({
    key: book, book,
    home: lines.home?.closing?.toFixed(2),
    draw: lines.draw?.closing?.toFixed(2),
    away: lines.away?.closing?.toFixed(2),
  }));
  return (
    <Table
      size="small" pagination={false} dataSource={rows}
      columns={[
        { title: "博彩", dataIndex: "book" },
        { title: "主胜", dataIndex: "home", align: "right" },
        { title: "平", dataIndex: "draw", align: "right" },
        { title: "客胜", dataIndex: "away", align: "right" },
      ]}
    />
  );
}
