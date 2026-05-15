import { useEffect, useState } from "react";
import { Drawer, Spin } from "antd";
import dayjs from "dayjs";
import { browseApi } from "../services/browse";
import type { FixtureDetail } from "../types/browse";

interface Props {
  fixtureId: number | null;
  open: boolean;
  onClose: () => void;
}

const PICK_LABEL: Record<string, string> = { H: "主胜", D: "平", A: "客胜" };

export default function FixtureDetailDrawer({ fixtureId, open, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<FixtureDetail | null>(null);

  useEffect(() => {
    if (!open || fixtureId == null) {
      setDetail(null);
      return;
    }
    setLoading(true);
    browseApi
      .getFixtureDetail(fixtureId)
      .then((d) => setDetail(d))
      .catch((err) => {
        console.error(err);
        setDetail(null);
      })
      .finally(() => setLoading(false));
  }, [fixtureId, open]);

  const home = detail?.home_team?.name ?? "";
  const away = detail?.away_team?.name ?? "";
  const ko = detail?.kickoff_utc ? dayjs(detail.kickoff_utc).format("YYYY-MM-DD HH:mm") : "—";
  const a = detail?.analysis;

  return (
    <Drawer
      title="比赛详情"
      placement="right"
      width={640}
      onClose={onClose}
      open={open}
      destroyOnClose
    >
      {loading ? (
        <Spin style={{ display: "block", margin: "50px auto" }} />
      ) : detail ? (
        <div className="fixture-detail">
          <section className="fd-overview">
            <h3 className="fd-teams">
              <span className="fd-team-home">{home}</span>
              <span className="fd-vs"> vs </span>
              <span className="fd-team-away">{away}</span>
            </h3>
            <div className="fd-row">
              <span className="fd-label">开球</span>
              <span className="fd-val">{ko}</span>
            </div>
            <div className="fd-row">
              <span className="fd-label">联赛</span>
              <span className="fd-val">{detail.league?.name ?? "—"}</span>
            </div>
          </section>

          <section className="fd-analysis">
            <h4>分析</h4>
            {a ? (
              <>
                <div className="fd-row">
                  <span className="fd-label">推荐</span>
                  <span className="fd-val fd-pick">{PICK_LABEL[a.pick]}</span>
                </div>
                <div className="fd-row">
                  <span className="fd-label">EV</span>
                  <span className="fd-val">
                    {a.ev !== undefined ? `${(a.ev * 100).toFixed(1)}%` : "—"}
                  </span>
                </div>
                <div className="fd-row">
                  <span className="fd-label">置信度</span>
                  <span className="fd-val">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <span key={i} className={`star ${i <= a.confidence_stars ? "on" : ""}`}>★</span>
                    ))}
                  </span>
                </div>
                <div className="fd-row">
                  <span className="fd-label">模型概率</span>
                  <span className="fd-val">
                    H {(a.model_prob.H * 100).toFixed(1)}% / D {(a.model_prob.D * 100).toFixed(1)}% / A {(a.model_prob.A * 100).toFixed(1)}%
                  </span>
                </div>
                {a.analyst_summary && <div className="fd-summary">{a.analyst_summary}</div>}
              </>
            ) : (
              <div className="fd-empty">暂无分析</div>
            )}
          </section>
        </div>
      ) : (
        <div className="fd-empty">未找到比赛数据</div>
      )}
    </Drawer>
  );
}
