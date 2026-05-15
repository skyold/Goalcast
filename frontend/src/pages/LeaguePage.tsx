import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Typography, Tabs, Table, Alert } from "antd";
import dayjs from "dayjs";
import { browseApi } from "../services/browse";
import type { Competition, Fixture } from "../types/browse";

export default function LeaguePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const compId = Number(id);
  const [league, setLeague] = useState<Competition | null>(null);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [standingsUnavailable, setStandingsUnavailable] = useState(false);

  useEffect(() => {
    browseApi.getCompetitions().then((items) => {
      setLeague(items.find((c) => c.id === compId) ?? null);
    });
    const today = dayjs().format("YYYY-MM-DD");
    browseApi.getFixtures({ date: today, competitionId: compId }).then(setFixtures);
    browseApi.getStandings(compId).then((v) => setStandingsUnavailable(v === null));
  }, [compId]);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ color: "#555d72", fontSize: 11, marginBottom: 6 }}>
        <Link to="/">浏览</Link> ▸ {league?.country} ▸ {league?.name}
      </div>
      <Typography.Title level={3}>{league?.name ?? `League ${compId}`}</Typography.Title>
      <Tabs
        items={[
          {
            key: "fixtures", label: "赛程",
            children: (
              <Table
                size="small" rowKey="fixture_id" dataSource={fixtures}
                onRow={(r) => ({ onClick: () => navigate(`/fixture/${r.fixture_id}`), style: { cursor: "pointer" } })}
                pagination={false}
                columns={[
                  { title: "KO", dataIndex: "kickoff_utc",
                    render: (v?: string) => v ? dayjs(v).format("MM-DD HH:mm") : "—" },
                  { title: "对阵", dataIndex: "name" },
                  { title: "赔率", dataIndex: "closing", align: "right",
                    render: (v?: number) => v?.toFixed(2) ?? "—" },
                  { title: "跌水", dataIndex: "drop_percentage", align: "right",
                    render: (v?: number) => v != null ? `${v.toFixed(1)}%` : "—" },
                ]}
              />
            ),
          },
          {
            key: "standings", label: "积分榜",
            children: standingsUnavailable
              ? <Alert type="info" message="此联赛暂无积分榜数据" />
              : <div>加载中...</div>,
          },
        ]}
      />
    </div>
  );
}
