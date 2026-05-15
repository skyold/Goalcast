import dayjs from "dayjs";
import type { Fixture } from "../types/browse";
import AnalysisBadge from "./AnalysisBadge";

interface Props {
  fixture: Fixture;
  analysis?: { ev?: number; stars?: number; pick?: "H" | "D" | "A" };
  onClick: (fixtureId: number) => void;
}

function splitName(name?: string): [string, string] {
  if (!name) return ["", ""];
  const parts = name.split(/\s+vs\s+/i);
  return [parts[0] ?? "", parts[1] ?? ""];
}

export default function FixtureCard({ fixture, analysis, onClick }: Props) {
  const [home, away] = splitName(fixture.name);
  const ko = fixture.kickoff_utc ? dayjs(fixture.kickoff_utc).format("HH:mm") : "—";
  const drop = fixture.drop_percentage ?? 0;

  return (
    <div className="fixture-card" onClick={() => onClick(fixture.fixture_id)}>
      <div className="fc-head">
        <span>⚽ {fixture.league?.name ?? "—"}</span>
        <span>{ko} KO</span>
      </div>
      <div className="fc-teams">
        <div className="fc-team">{home}</div>
        <div className="fc-team">{away}</div>
      </div>
      <div className="fc-odds">
        {fixture.closing != null && (
          <div className="fc-odd best">
            <div className="lbl">当前</div>
            <div className="val">{fixture.closing.toFixed(2)}</div>
          </div>
        )}
        {fixture.opening != null && (
          <div className="fc-odd">
            <div className="lbl">开盘</div>
            <div className="val">{fixture.opening.toFixed(2)}</div>
          </div>
        )}
        {drop !== 0 && (
          <div className="fc-odd drop">
            <div className="lbl">跌水</div>
            <div className="val">{drop.toFixed(1)}%</div>
          </div>
        )}
      </div>
      <div className="fc-footer">
        <AnalysisBadge ev={analysis?.ev} stars={analysis?.stars} pick={analysis?.pick} />
      </div>
    </div>
  );
}
