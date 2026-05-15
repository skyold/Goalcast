interface Series { home: number[]; draw: number[]; away: number[]; }

interface Props {
  data: Series | null;
  width?: number;
  height?: number;
}

export default function OddsCurveChart({ data, width = 480, height = 140 }: Props) {
  if (!data || data.home.length === 0) {
    return <div style={{ color: "#555d72", padding: 20 }}>无数据</div>;
  }
  const all = [...data.home, ...data.draw, ...data.away];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const padding = { x: 20, y: 20 };

  function points(arr: number[]): string {
    const stepX = (width - padding.x * 2) / (arr.length - 1 || 1);
    return arr.map((v, i) => {
      const x = padding.x + i * stepX;
      const y = padding.y + (1 - (v - min) / (max - min || 1)) * (height - padding.y * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
  }

  return (
    <div className="chart-wrap">
      <div className="chart-legend">
        <span><span className="dot" style={{ background: "#00FF9D" }} />主胜</span>
        <span><span className="dot" style={{ background: "#555d72" }} />平</span>
        <span><span className="dot" style={{ background: "#60a5fa" }} />客胜</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height}>
        <polyline points={points(data.home)} fill="none" stroke="#00FF9D" strokeWidth="2" />
        <polyline points={points(data.draw)} fill="none" stroke="#555d72" strokeWidth="2" strokeDasharray="3,3" />
        <polyline points={points(data.away)} fill="none" stroke="#60a5fa" strokeWidth="2" />
      </svg>
    </div>
  );
}
