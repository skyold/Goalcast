interface Props { homeStats?: Record<string, any>; awayStats?: Record<string, any>; }

const FIELDS: Array<[string, string]> = [
  ["xg_for", "xG (for)"],
  ["xg_against", "xG (against)"],
  ["goals_for_avg", "场均进球"],
  ["goals_against_avg", "场均失球"],
];

export default function StatsCompare({ homeStats = {}, awayStats = {} }: Props) {
  return (
    <div className="stats-compare">
      {FIELDS.map(([k, label]) => {
        const h = homeStats[k]; const a = awayStats[k];
        if (h == null && a == null) return null;
        return (
          <div key={k} className="row">
            <span className="left">{h ?? "—"}</span>
            <span className="label">{label}</span>
            <span className="right">{a ?? "—"}</span>
          </div>
        );
      })}
    </div>
  );
}
