interface Point {
  t: number | string;
  value: number;
}

interface Props {
  points: Point[];
  width?: number;
  height?: number;
  stroke?: string;
}

export default function OddsCurveChart({
  points,
  width = 320,
  height = 120,
  stroke = "#a3e635",
}: Props) {
  if (!points || points.length === 0) {
    return <div className="odds-curve-empty">暂无数据</div>;
  }

  const pad = 8;
  const w = width - pad * 2;
  const h = height - pad * 2;

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const n = points.length;
  const polyPoints = points
    .map((p, i) => {
      const x = pad + (n === 1 ? w / 2 : (i / (n - 1)) * w);
      const y = pad + h - ((p.value - min) / range) * h;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <svg
      className="odds-curve"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="odds curve"
    >
      <rect className="odds-curve-bg" x={0} y={0} width={width} height={height} />
      <polyline
        className="odds-curve-line"
        fill="none"
        stroke={stroke}
        strokeWidth={2}
        points={polyPoints}
      />
      {points.map((p, i) => {
        const x = pad + (n === 1 ? w / 2 : (i / (n - 1)) * w);
        const y = pad + h - ((p.value - min) / range) * h;
        return (
          <circle
            key={i}
            className="odds-curve-dot"
            cx={x}
            cy={y}
            r={2.5}
            fill={stroke}
          />
        );
      })}
    </svg>
  );
}
