import { useAppStore } from "../store/appStore";
import { Tag } from "antd";
import { PlayCircleOutlined } from "@ant-design/icons";

export default function DashboardExtras() {
  const pipelineStatus = useAppStore((s) => s.pipelineStatus);
  const pipelineMatches = useAppStore((s) => s.pipelineMatches);
  const activeLeagues = useAppStore((s) => s.activeLeagues);

  const matchList = Object.values(pipelineMatches);
  const doneCount = matchList.filter((m) => m.status === "done").length;
  const errorCount = matchList.filter((m) => m.status === "error").length;
  const total = matchList.length;

  return (
    <div
      style={{
        background: "var(--card-bg)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: "12px 20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <PlayCircleOutlined
          style={{
            color: pipelineStatus.includes("Running") ? "#00FF9D" : "var(--text-muted)",
            fontSize: 18,
          }}
        />
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
          Pipeline Status
        </span>
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
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {activeLeagues.join(", ")}
          </span>
        )}
      </div>

      {total > 0 && (
        <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--text-secondary)" }}>
          <span>
            Analyzed: {doneCount}/{total}
          </span>
          {errorCount > 0 && <span style={{ color: "#ef4444" }}>Errors: {errorCount}</span>}
        </div>
      )}
    </div>
  );
}
