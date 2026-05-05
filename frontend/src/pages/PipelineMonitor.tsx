import { useAppStore } from "../store/appStore";
import { Card, Tag, Progress, Empty } from "antd";
import {
  ClockCircleOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
} from "@ant-design/icons";

interface MatchCard {
  match_id: string;
  home_team: string;
  away_team: string;
  kickoff_time: string;
  status: "pending" | "analyzing" | "trading" | "done" | "error";
  predictions?: { home_win?: number; draw?: number; away_win?: number };
  ev?: number;
  recommendation?: string;
  error?: string;
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "pending":
      return <ClockCircleOutlined style={{ color: "var(--text-muted)" }} />;
    case "analyzing":
    case "trading":
      return <LoadingOutlined style={{ color: "#00FF9D" }} spin />;
    case "done":
      return <CheckCircleOutlined style={{ color: "var(--green)" }} />;
    case "error":
      return <CloseCircleOutlined style={{ color: "#ef4444" }} />;
    default:
      return <ClockCircleOutlined style={{ color: "var(--text-muted)" }} />;
  }
}

function MatchCardView({ match }: { match: MatchCard }) {
  return (
    <Card
      size="small"
      style={{
        background: "var(--card-bg)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
      }}
      title={
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#00FF9D" }}>
            {match.match_id.substring(0, 8)}
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <StatusIcon status={match.status} />
            <Tag
            color={
              match.status === "done"
                ? "green"
                : match.status === "error"
                ? "red"
                : match.status === "analyzing" || match.status === "trading"
                ? "processing"
                : "default"
            }
          >
            {match.status}
          </Tag>
          </div>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
            {match.home_team}
          </div>
          <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
            vs {match.away_team}
          </div>
        </div>

        {match.kickoff_time && (
          <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {match.kickoff_time}
          </div>
        )}

        {match.status === "analyzing" || match.status === "trading" ? (
          <Progress percent={50} status="active" strokeColor="#00FF9D" showInfo={false} />
        ) : match.status === "done" && match.predictions ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", height: 4, borderRadius: 2, overflow: "hidden", gap: 1 }}>
              <div
                style={{
                  flex: (match.predictions.home_win || 0) * 100,
                  background: "#00FF9D",
                }}
              />
              <div
                style={{
                  flex: (match.predictions.draw || 0) * 100,
                  background: "var(--text-muted)",
                }}
              />
              <div
                style={{
                  flex: (match.predictions.away_win || 0) * 100,
                  background: "#3b82f6",
                }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Recommendation
                </div>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "var(--text-primary)",
                    background: "var(--nav-bg)",
                    padding: "2px 8px",
                    borderRadius: 4,
                    border: "1px solid var(--border)",
                    display: "inline-block",
                  }}
                >
                  {match.recommendation || "No Bet"}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>EV</div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 18,
                    fontWeight: 700,
                    color:
                      (match.ev || 0) > 1.05
                        ? "#00FF9D"
                        : (match.ev || 0) > 1.0
                        ? "#ff9500"
                        : "#ef4444",
                  }}
                >
                  {match.ev ? match.ev.toFixed(3) : "—"}
                </div>
              </div>
            </div>
          </div>
        ) : match.status === "error" && match.error ? (
          <div style={{ color: "#ef4444", fontSize: 12, display: "flex", alignItems: "flex-start", gap: 6 }}>
            <CloseCircleOutlined />
            <span>{match.error}</span>
          </div>
        ) : (
          <div style={{ color: "var(--text-muted)", fontSize: 12, textAlign: "center", padding: "8px 0" }}>
            <ClockCircleOutlined style={{ marginRight: 6 }} />
            Waiting...
          </div>
        )}
      </div>
    </Card>
  );
}

export default function PipelineMonitor() {
  const pipelineMatches = useAppStore((s) => s.pipelineMatches);
  const pipelineStatus = useAppStore((s) => s.pipelineStatus);
  const activeLeagues = useAppStore((s) => s.activeLeagues);
  const wsConnected = useAppStore((s) => s.wsConnected);

  const matchList = Object.values(pipelineMatches);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 20px",
          background: "var(--card-bg)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <PlayCircleOutlined style={{ color: "#00FF9D", fontSize: 18 }} />
            <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
              Pipeline Monitor
            </span>
          </div>
          <Tag
            color={
              pipelineStatus.includes("Running")
                ? "processing"
                : pipelineStatus === "Completed"
                ? "green"
                : "default"
            }
          >
            {pipelineStatus || "Idle"}
          </Tag>
          {activeLeagues.length > 0 && (
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              Leagues: {activeLeagues.join(", ")}
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: wsConnected ? "var(--green)" : "#ef4444",
              boxShadow: wsConnected ? "0 0 6px var(--green)" : "none",
            }}
          />
          <span
            style={{
              fontSize: 11,
              color: wsConnected ? "var(--green)" : "#ef4444",
              fontFamily: "var(--font-mono)",
            }}
          >
            {wsConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      {matchList.length === 0 ? (
        <Empty
          description="No active pipeline. Send a request via Chat to start."
          style={{ padding: 60 }}
        />
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 12,
          }}
        >
          {matchList.map((match) => (
            <MatchCardView key={match.match_id} match={match} />
          ))}
        </div>
      )}
    </div>
  );
}
