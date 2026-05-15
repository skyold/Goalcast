export default function Skeleton({ width = '100%', height = 16, style }: { width?: string | number; height?: string | number; style?: React.CSSProperties }) {
  return (
    <div style={{ width, height, borderRadius:4, background:'linear-gradient(90deg,#1a2d47 25%,#243a57 50%,#1a2d47 75%)', backgroundSize:'200% 100%', animation:'shimmer 1.5s infinite', ...style }} />
  )
}
