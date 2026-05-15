import { Tabs, Empty, Typography } from "antd";
import { Link } from "react-router-dom";
import { useFavorites } from "../store/favorites";

export default function FavoritesPage() {
  const { fixtures, leagues, teams } = useFavorites();
  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>⭐ 我的关注</Typography.Title>
      <Tabs
        items={[
          {
            key: "fixtures", label: `关注比赛 (${fixtures.length})`,
            children: fixtures.length === 0 ? <Empty /> : (
              <ul>{fixtures.map((id) => <li key={id}><Link to={`/fixture/${id}`}>Fixture #{id}</Link></li>)}</ul>
            ),
          },
          {
            key: "leagues", label: `关注联赛 (${leagues.length})`,
            children: leagues.length === 0 ? <Empty /> : (
              <ul>{leagues.map((id) => <li key={id}><Link to={`/league/${id}`}>League #{id}</Link></li>)}</ul>
            ),
          },
          {
            key: "teams", label: `关注球队 (${teams.length})`,
            children: teams.length === 0 ? <Empty /> : (
              <ul>{teams.map((id) => <li key={id}><Link to={`/team/${id}`}>Team #{id}</Link></li>)}</ul>
            ),
          },
          { key: "bets", label: "下注记录", children: <Link to="/my/bets">查看下注记录 →</Link> },
        ]}
      />
    </div>
  );
}
