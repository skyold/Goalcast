import { useEffect, useState } from "react";
import { Tabs, Typography, Empty } from "antd";
import { useNavigate, useParams } from "react-router-dom";
import { browseApi } from "../services/browse";
import type { TrendItem, TrendType } from "../types/browse";

const TYPES: { key: TrendType; label: string }[] = [
  { key: "home_win", label: "主胜趋势" },
  { key: "away_win", label: "客胜趋势" },
  { key: "btts", label: "BTTS 趋势" },
  { key: "over25", label: "大球趋势" },
];

export default function TrendsPage() {
  const { type } = useParams<{ type: TrendType }>();
  const navigate = useNavigate();
  const active = (type ?? "home_win") as TrendType;
  const [items, setItems] = useState<TrendItem[]>([]);

  useEffect(() => {
    browseApi.getTrends(active).then(setItems).catch(console.error);
  }, [active]);

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>📈 OddAlerts 趋势榜</Typography.Title>
      <Tabs
        activeKey={active}
        onChange={(k) => navigate(`/trends/${k}`)}
        items={TYPES.map(({ key, label }) => ({ key, label }))}
      />
      {items.length === 0 ? (
        <Empty />
      ) : (
        <div className="trend-grid">
          {items.map((t, i) => (
            <div key={t.fixture_id} className="trend-card" onClick={() => navigate(`/fixture/${t.fixture_id}`)}>
              <div className="rank">#{i + 1}</div>
              <div className="pair">{t.fixture_name ?? `Fixture ${t.fixture_id}`}</div>
              <div className="prob">{(t.probability * 100).toFixed(1)}%</div>
              <div className="meta">赔率 {t.odds?.toFixed(2) ?? "—"}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
