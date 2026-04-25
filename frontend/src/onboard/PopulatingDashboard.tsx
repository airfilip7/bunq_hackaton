import { useEffect } from 'react'
import { useMotionValue, useTransform, animate, motion } from 'framer-motion'
import type { ProfileSnapshot } from '@/api/types'

function AnimatedNumber({ to, format }: { to: number; format: (n: number) => string }) {
  const mv = useMotionValue(0)
  const display = useTransform(mv, (v) => format(Math.round(v)))

  useEffect(() => {
    const controls = animate(mv, to, { duration: 0.9, ease: 'easeOut' })
    return controls.stop
  }, [mv, to])

  return <motion.span className="t-num">{display}</motion.span>
}

function fmt(n: number) {
  return '\u20AC' + n.toLocaleString('nl-NL')
}

type Props = { profile: ProfileSnapshot }

export function PopulatingDashboard({ profile }: Props) {
  const { projection } = profile

  const stats = [
    {
      label: 'Gap',
      node: <AnimatedNumber to={projection.gap_eur} format={fmt} />,
      sub: `Target ${fmt(projection.deposit_target_eur)}`,
    },
    {
      label: 'Months',
      node: <AnimatedNumber to={projection.months_to_goal} format={(n) => `${n}`} />,
      sub: 'to deposit',
    },
    {
      label: 'Headroom',
      node: (
        <span className="t-num" style={{ color: 'var(--violet-2)', fontSize: 16 }}>
          {fmt(projection.headroom_range_eur[0])}\u2013{fmt(projection.headroom_range_eur[1])}
        </span>
      ),
      sub: 'per Nibud norms',
    },
  ]

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 1fr 1.3fr',
      gap: 1,
      background: 'var(--line)',
      borderRadius: 18,
      overflow: 'hidden',
      border: '1px solid var(--line)',
    }}>
      {stats.map((s) => (
        <div key={s.label} style={{
          background: 'rgba(255,255,255,0.04)',
          padding: '14px 16px 16px',
          display: 'flex', flexDirection: 'column', gap: 4,
        }}>
          <div className="t-caption" style={{ fontSize: 10, letterSpacing: '0.08em' }}>{s.label}</div>
          <div style={{ fontSize: 19, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink)', lineHeight: 1.1 }}>
            {s.node}
          </div>
          <div style={{ fontSize: 10, color: 'var(--ink-3)', fontWeight: 500 }}>{s.sub}</div>
        </div>
      ))}
    </div>
  )
}
