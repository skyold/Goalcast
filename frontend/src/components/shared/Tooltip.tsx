import * as RT from '@radix-ui/react-tooltip'
import type { ReactNode } from 'react'

interface Props {
  content: ReactNode
  children: ReactNode
  side?: 'top' | 'right' | 'bottom' | 'left'
  sideOffset?: number
}

// Wraps a single trigger element. Hover + keyboard focus + ESC handled by Radix.
// Visual styling lives in themes.css under .gc-tt.
export function Tooltip({ content, children, side = 'top', sideOffset = 6 }: Props) {
  if (content == null || content === '') return <>{children}</>
  return (
    <RT.Provider delayDuration={200} skipDelayDuration={100}>
      <RT.Root>
        <RT.Trigger asChild>{children}</RT.Trigger>
        <RT.Portal>
          <RT.Content className="gc-tt" side={side} sideOffset={sideOffset} collisionPadding={8}>
            {content}
            <RT.Arrow className="gc-tt-arrow" width={10} height={5} />
          </RT.Content>
        </RT.Portal>
      </RT.Root>
    </RT.Provider>
  )
}

export default Tooltip
