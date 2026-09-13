export type Rect = { x: number; y: number; width: number; height: number }
export function placeCard(target: Rect | null, width: number, height: number, viewport: Rect): Rect & { side: string } {
  const pad = 12, gap = 16, w = Math.min(width, viewport.width - pad * 2), h = Math.min(height, viewport.height - pad * 2)
  const clampX = (x: number) => Math.max(viewport.x + pad, Math.min(x, viewport.x + viewport.width - w - pad))
  const clampY = (y: number) => Math.max(viewport.y + pad, Math.min(y, viewport.y + viewport.height - h - pad))
  if (!target) return { x: clampX(viewport.x + (viewport.width - w) / 2), y: clampY(viewport.y + (viewport.height - h) / 2), width: w, height: h, side: 'center' }
  const choices = [
    { side: 'right', x: target.x + target.width + gap, y: clampY(target.y), room: viewport.x + viewport.width - (target.x + target.width) - gap - pad, need: w },
    { side: 'left', x: target.x - w - gap, y: clampY(target.y), room: target.x - viewport.x - gap - pad, need: w },
    { side: 'bottom', x: clampX(target.x), y: target.y + target.height + gap, room: viewport.y + viewport.height - target.y - target.height - gap - pad, need: h },
    { side: 'top', x: clampX(target.x), y: target.y - h - gap, room: target.y - viewport.y - gap - pad, need: h },
  ]
  const fit = choices.find(c => c.room >= c.need)
  if (fit) return { ...fit, width: w, height: h }
  // Narrow screens reserve the larger vertical space for a scrollable explanation.
  const vertical = choices.slice(2).sort((a, b) => b.room - a.room)[0]!
  const capped = Math.max(90, Math.min(h, vertical.room))
  return { x: clampX(target.x), y: Math.max(viewport.y + pad, Math.min(vertical.side === 'top' ? target.y - capped - gap : target.y + target.height + gap, viewport.y + viewport.height - capped - pad)), width: w, height: capped, side: vertical.side }
}
