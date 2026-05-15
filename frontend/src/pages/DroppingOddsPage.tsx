import { useEffect, useState } from "react";
import { Table, Tag, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import { browseApi } from "../services/browse";
import type { DroppingOdd } from "../types/browse";

const DROP_OPTIONS = [5, 8, 12];
const WINDOW_OPTIONS = ["1h", "6h", "24h"] as const;

export default function DroppingOddsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<DroppingOdd[]>([]);
  const [minDrop, setMinDrop] = useState(8);
  const [windowSel, setWindowSel] = useState<"1h" | "6h" | "24h">("24h");

  useEffect(() => {
    browseApi.getDropping({ minDrop, window: windowSel })
      .then(setItems)
      .catch(console.error);
  }, [minDrop, windowSel]);

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>🔥 跌水赔率榜</Typography.Title>
      <Space style={{ marginBottom: 16 }} wrap>
        <span style={{ color: "#555d72" }}>跌幅：</span>
        {DROP_OPTIONS.map((d) => (
          <Tag.CheckableTag key={d} checked={minDrop === d} onChange={() => setMinDrop(d)}>
            ≥{d}%
          </Tag.CheckableTag>
        ))}
        <span style={{ color: "#555d72", marginLeft: 14 }}>时间：</span>
        {WINDOW_OPTIONS.map((w) => (
          <Tag.CheckableTag key={w} checked={windowSel === w} onChange={() => setWindowSel(w)}>
            {w}
          </Tag.CheckableTag>
        ))}
      </Space>
      <Table
        size="small"
        rowKey={(r) => `${r.fixture_id}-${r.bookmaker ?? ""}`}
        dataSource={items}
        onRow={(r) => ({ onClick: () => navigate(`/fixture/${r.fixture_id}`), style: { cursor: "pointer" } })}
        pagination={{ pageSize: 30 }}
        columns={[
          { title: "KO", dataIndex: "starting_at",
            render: (v?: string) => v ? dayjs(v).format("MM-DD HH:mm") : "—" },
          { title: "联赛", dataIndex: ["league", "name"] },
          { title: "对阵", dataIndex: "fixture_name" },
          { title: "开盘", dataIndex: "opening", align: "right",
            render: (v?: number) => v?.toFixed(2) ?? "—" },
          { title: "当前", dataIndex: "closing", align: "right",
            render: (v?: number) => v != null ? <span style={{ color: "#00FF9D" }}>{v.toFixed(2)}</span> : "—" },
          { title: "跌幅", dataIndex: "drop_percentage", align: "right",
            render: (v?: number) => v != null ? <span style={{ color: "#ef4444" }}>{v.toFixed(1)}%</span> : "—" },
          { title: "博彩", dataIndex: "bookmaker" },
        ]}
      />
    </div>
  );
}
