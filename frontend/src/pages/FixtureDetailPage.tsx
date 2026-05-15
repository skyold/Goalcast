import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Tabs, Statistic, Row, Col, Button, Spin } from "antd";
import dayjs from "dayjs";
import { browseApi } from "../services/browse";
import type { FixtureDetail } from "../types/browse";
import MarketDepthTable from "../components/MarketDepthTable";
import StatsCompare from "../components/StatsCompare";
import H2HTable from "../components/H2HTable";
import AnalysisBadge from "../components/AnalysisBadge";

export default function FixtureDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<FixtureDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    browseApi.getFixtureDetail(Number(id))
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin />;
  if (!data) return <div>赛事未找到</div>;

  const a = data.analysis;
  const modelHpct = a ? (a.model_prob.H * 100).toFixed(1) : "—";
  const evPct = a?.ev != null ? (a.ev * 100).toFixed(1) : "—";
  const kellyPct = a?.kelly != null ? (a.kelly * 100).toFixed(2) : "—";

  return (
    <div className="fixture-detail">
      <div className="fdp-breadcrumb">
        <Link to="/">浏览</Link>
        {data.league?.id && <> ▸ <Link to={`/league/${data.league.id}`}>{data.league.name}</Link></>}
        {" ▸ "}{data.home_team?.name} vs {data.away_team?.name}
      </div>
      <div className="fdp-hero">
        <div className="fdp-team">
          <div className="logo">{data.home_team?.name?.slice(0, 3)}</div>
          <div>{data.home_team?.name}</div>
        </div>
        <div className="fdp-vs">
          <div className="ko">{dayjs(data.kickoff_utc).format("YYYY-MM-DD HH:mm")}</div>
          <div className="meta">{data.league?.name}</div>
        </div>
        <div className="fdp-team">
          <div className="logo">{data.away_team?.name?.slice(0, 3)}</div>
          <div>{data.away_team?.name}</div>
        </div>
        <div className="fdp-actions">
          <Button onClick={() => navigate(-1)}>← 返回</Button>
          <Button type="primary">🔄 重新分析</Button>
        </div>
      </div>
      <Row gutter={12} className="fdp-kpi">
        <Col span={6}><Statistic title="模型 P(H)" value={modelHpct} suffix="%" /></Col>
        <Col span={6}><Statistic title="EV (主胜)" value={evPct} suffix="%" /></Col>
        <Col span={6}><Statistic title="Kelly" value={kellyPct} suffix="%" /></Col>
        <Col span={6}>
          <div style={{ color: "#9ba3b8", fontSize: 12 }}>置信</div>
          <AnalysisBadge ev={a?.ev} stars={a?.confidence_stars} pick={a?.pick} />
        </Col>
      </Row>
      <Tabs
        items={[
          { key: "depth", label: "赔率深度",
            children: <MarketDepthTable history={data.odds_history} /> },
          { key: "stats", label: "统计对比",
            children: <StatsCompare homeStats={data.stats_home} awayStats={data.stats_away} /> },
          { key: "h2h", label: "H2H", children: <H2HTable h2h={data.h2h} /> },
          { key: "json", label: "JSON 原始",
            children: <pre style={{ maxHeight: 400, overflow: "auto" }}>{JSON.stringify(data, null, 2)}</pre> },
        ]}
      />
    </div>
  );
}
