import { useEffect, useRef, useState } from 'react'

const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

/**
 * A figure that counts to its value when it first appears or changes.
 *
 * It makes a new number noticeable without decorating it: 480 ms on a decelerating curve,
 * from the previous value (or zero), and the final text is exactly what `format` returns,
 * so nothing a person copies or a test reads differs from the static rendering. With
 * reduced motion the value is simply shown.
 */
export function CountUp({ value, format }: { value: number; format: (value: number) => string }) {
  const [shown, setShown] = useState(() => reduced() ? value : 0)
  const from = useRef(reduced() ? value : 0)
  useEffect(() => {
    if (reduced() || !Number.isFinite(value)) { setShown(value); from.current = value; return }
    const start = performance.now(), origin = from.current
    // In-between values carry no more decimals than the value itself: a count of items steps
    // through whole numbers, never "2.37".
    const places = Math.min(4, (String(value).split('.')[1] ?? '').length)
    const settle = (x: number) => Number(x.toFixed(places))
    let frame = 0
    const step = (now: number) => {
      const progress = Math.min(1, (now - start) / 480)
      const eased = 1 - (1 - progress) ** 3
      setShown(progress === 1 ? value : settle(origin + (value - origin) * eased))
      if (progress < 1) frame = requestAnimationFrame(step)
      else from.current = value
    }
    frame = requestAnimationFrame(step)
    return () => { cancelAnimationFrame(frame); from.current = value }
  }, [value])
  return <span className="bf-count" aria-label={format(value)}>{format(shown)}</span>
}
