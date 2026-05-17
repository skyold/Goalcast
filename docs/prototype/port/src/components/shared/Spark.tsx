// Tiny SVG sparkline. Renders nothing if there are fewer than 2 points.
interface Props { values: number[]; color?: string; width?: number; height?: number }

export function Spark({ values, color, width = 64, height = 22 }: Props) {
  if (!values || values.length < 2) return null
  const min = Math.min(...values), max = Math.max(...values)
  const dx = width / (values.length - 1)
  const pts = values.map((v, i) => {
    const x = i * dx
    const y = max === min ? height / 2 : height - ((v - min) / (max - min)) * (height - 4) - 2
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="spark" style={{ overflow: 'visible' }}>
      <polyline points={pts} fill="none" stroke={color || 'currentColor'}
        strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
