const PICK_LABEL: Record<string, string> = { H: "主胜", D: "平", A: "客胜" };

interface Props {
  ev?: number;
  stars?: number;
  pick?: "H" | "D" | "A";
}

export default function AnalysisBadge({ ev, stars = 0, pick }: Props) {
  if (ev === undefined || pick === undefined) {
    return <span className="analysis-badge muted">观望</span>;
  }
  const evPct = (ev * 100).toFixed(1);
  return (
    <span className="analysis-badge">
      <span className="ev">{ev >= 0 ? "+" : ""}{evPct}%</span>
      <span className="pick">{PICK_LABEL[pick]}</span>
      <span className="stars">
        {[1, 2, 3, 4, 5].map((i) => (
          <span key={i} className={`star ${i <= stars ? "on" : ""}`}>★</span>
        ))}
      </span>
    </span>
  );
}
