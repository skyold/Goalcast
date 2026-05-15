import { useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import type { FixtureSummary } from '../../lib/api'
import MatchCard from './MatchCard'

export default function MatchCardGrid({ fixtures }: { fixtures: FixtureSummary[] }) {
  const parentRef = useRef<HTMLDivElement>(null)
  const rowCount = Math.ceil(fixtures.length / 2)

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 232,
    overscan: 3,
  })

  return (
    <div ref={parentRef} style={{ height:'calc(100vh - 57px)', overflowY:'auto' }}>
      <div style={{ height:virtualizer.getTotalSize(), position:'relative' }}>
        {virtualizer.getVirtualItems().map((row) => {
          const left = fixtures[row.index * 2]
          const right = fixtures[row.index * 2 + 1]
          return (
            <div key={row.key} data-index={row.index} ref={virtualizer.measureElement}
              style={{ position:'absolute', top:row.start, left:0, right:0, display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, padding:'6px 16px' }}>
              {left && <MatchCard fixture={left} />}
              {right && <MatchCard fixture={right} />}
            </div>
          )
        })}
      </div>
    </div>
  )
}
