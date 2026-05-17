// Team color/abbr tile. Resolves abbr+color from teamMeta — see lib/teamMeta.ts.
import { teamMeta } from '../../lib/teamMeta'

interface Props { name: string; teamId?: number | null; size?: number }

export function TeamAbbr({ name, teamId, size = 26 }: Props) {
  const m = teamMeta({ id: teamId, name })
  return (
    <span
      className="mc-abbr"
      style={{
        background: m.color,
        width: size,
        height: size,
        fontSize: Math.round(size * 0.36),
      }}
    >
      {m.abbr}
    </span>
  )
}
