import { useEffect, useState } from "react";
import { Button, Table, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import { browseApi } from "../services/browse";
import AnalysisBadge from "../components/AnalysisBadge";

interface Row {
  fixture_id: number;
  name?: string;
  analysis: any;
}

export default function AnalysisReportsPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Row[]>([]);
  const [running, setRunning] = useState(false);

  const load = () => browseApi.getAnalysisRecent(50).then((items) => setRows(items as Row[]));
  useEffect(() => { load(); }, []);

  const trigger = async () => {
    setRunning(true);
    try {
      const r = await browseApi.runAnalysis();
      message.success(`分析已触发 (run_id=${r.run_id})`);
      setTimeout(load, 2000);
    } catch (e) {
      message.error(`触发失败: ${e}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography.Title level={3}>📊 自研分析报告</Typography.Title>
        <Button type="primary" onClick={trigger} loading={running}>▶ 触发新一轮</Button>
      </div>
      <Table
        size="small" rowKey="fixture_id" dataSource={rows}
        onRow={(r) => ({ onClick: () => navigate(`/fixture/${r.fixture_id}`), style: { cursor: "pointer" } })}
        columns={[
          { title: "比赛", dataIndex: "name", render: (v?: string, r) => v ?? `Fixture ${r.fixture_id}` },
          { title: "推荐", dataIndex: ["analysis", "pick"] },
          { title: "EV", dataIndex: ["analysis", "ev"],
            render: (v?: number) => v != null ? `${(v * 100).toFixed(1)}%` : "—" },
          { title: "置信",
            render: (_, r) => <AnalysisBadge ev={r.analysis?.ev} stars={r.analysis?.confidence_stars} pick={r.analysis?.pick} /> },
        ]}
      />
    </div>
  );
}
