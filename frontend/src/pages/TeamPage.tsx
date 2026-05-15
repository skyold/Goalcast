import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Typography, Descriptions, Alert, Spin } from "antd";
import { browseApi } from "../services/browse";
import type { TeamStats } from "../types/browse";

export default function TeamPage() {
  const { id } = useParams<{ id: string }>();
  const [team, setTeam] = useState<TeamStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    browseApi.getTeam(Number(id))
      .then(setTeam)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin />;
  if (!team) return <Alert type="warning" message="球队未找到" />;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>{team.name}</Typography.Title>
      <Descriptions bordered column={2} size="small">
        <Descriptions.Item label="场均进球">{team.goals_for_avg ?? "—"}</Descriptions.Item>
        <Descriptions.Item label="场均失球">{team.goals_against_avg ?? "—"}</Descriptions.Item>
        <Descriptions.Item label="xG (for)">{team.xg_for ?? "—"}</Descriptions.Item>
        <Descriptions.Item label="xG (against)">{team.xg_against ?? "—"}</Descriptions.Item>
      </Descriptions>
    </div>
  );
}
