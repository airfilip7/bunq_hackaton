import { useEffect } from 'react'
import { useMotionValue, useTransform, animate, motion } from 'framer-motion'
import type { ProfileSnapshot } from '@/api/types'

function AnimatedNumber({ to, prefix = '', suffix = '' }: { to: number; prefix?: string; suffix?: string }) {
  const mv = useMotionValue(0)
  const display = useTransform(mv, (v) => `${prefix}${Math.round(v).toLocaleString('nl-NL')}${suffix}`)

  useEffect(() => {
    const controls = animate(mv, to, { duration: 0.9, ease: 'easeOut' })
    return controls.stop
  }, [mv, to])

  return <motion.span>{display}</motion.span>
}

type Props = { profile: ProfileSnapshot }

export function PopulatingDashboard({ profile }: Props) {
  const { projection } = profile

  return (
    <div className="grid grid-cols-3 gap-4 p-6 bg-surface-1 rounded-2xl">
      <Stat
        label="Gap to deposit"
        value={<AnimatedNumber to={projection.gap_eur} prefix="€" />}
        sub={`Target €${projection.deposit_target_eur.toLocaleString('nl-NL')}`}
      />
      <Stat
        label="Months to goal"
        value={<AnimatedNumber to={projection.months_to_goal} suffix=" mo" />}
        sub={`Saving €${projection.monthly_savings_eur.toLocaleString('nl-NL')}/mo`}
      />
      <Stat
        label="Mortgage headroom"
        value={
          <span className="text-bunq-teal">
            €{projection.headroom_range_eur[0].toLocaleString('nl-NL')}
            {' – '}
            €{projection.headroom_range_eur[1].toLocaleString('nl-NL')}
          </span>
        }
        sub="per Nibud norms"
      />
    </div>
  )
}

function Stat({ label, value, sub }: { label: string; value: React.ReactNode; sub: string }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs text-text-secondary uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold text-text-primary">{value}</p>
      <p className="text-xs text-text-disabled">{sub}</p>
    </div>
  )
}
