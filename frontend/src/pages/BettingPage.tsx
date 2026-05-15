import { useEffect, useState, useMemo } from "react";
import { Layout, Segmented, DatePicker, Empty, Spin } from "antd";
import dayjs, { Dayjs } from "dayjs";
import { browseApi } from "../services/browse";
import type { Competition, Fixture } from "../types/browse";
import LeagueTree from "../components/LeagueTree";
import FixtureCard from "../components/FixtureCard";
import FixtureDetailDrawer from "../components/FixtureDetailDrawer";

const { Sider, Content } = Layout;

export default function BettingPage() {
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [date, setDate] = useState<Dayjs>(dayjs());
  const [selectedLeague, setSelectedLeague] = useState<number | undefined>();
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerFixtureId, setDrawerFixtureId] = useState<number | null>(null);

  useEffect(() => {
    browseApi.getCompetitions().then(setCompetitions).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    browseApi.getFixtures({
      date: date.format("YYYY-MM-DD"),
      competitionId: selectedLeague,
    })
      .then(setFixtures)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [date, selectedLeague]);

  const grouped = useMemo(() => {
    const g: Record<string, Fixture[]> = {};
    for (const f of fixtures) {
      const key = f.league?.name ?? "其他";
      (g[key] ||= []).push(f);
    }
    return Object.entries(g);
  }, [fixtures]);

  return (
    <Layout style={{ background: "transparent" }}>
      <Sider width={240} className="goalcast-aside" theme="dark">
        <LeagueTree
          competitions={competitions}
          selectedId={selectedLeague}
          onSelect={setSelectedLeague}
        />
      </Sider>
      <Content style={{ padding: "16px 22px" }}>
        <div className="filters">
          <DatePicker value={date} onChange={(d) => d && setDate(d)} allowClear={false} format="YYYY-MM-DD" />
          <Segmented
            options={[
              { label: "今天", value: 0 },
              { label: "明天", value: 1 },
              { label: "本周", value: 7 },
            ]}
            onChange={(v) => setDate(dayjs().add(Number(v), "day"))}
          />
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: 40 }}><Spin /></div>
        ) : fixtures.length === 0 ? (
          <Empty description="无赛事" />
        ) : (
          grouped.map(([league, items]) => (
            <div key={league} className="league-section">
              <h3 className="league-title">{league} <span>{items.length} 场</span></h3>
              <div className="fixture-grid">
                {items.map((f) => (
                  <FixtureCard
                    key={f.fixture_id}
                    fixture={f}
                    onClick={(id) => setDrawerFixtureId(id)}
                  />
                ))}
              </div>
            </div>
          ))
        )}

        <FixtureDetailDrawer
          fixtureId={drawerFixtureId}
          open={drawerFixtureId !== null}
          onClose={() => setDrawerFixtureId(null)}
        />
      </Content>
    </Layout>
  );
}
