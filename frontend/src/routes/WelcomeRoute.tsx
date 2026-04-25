import { useNavigate, useLocation } from 'react-router-dom'
import { Icon } from '@/components/Icon'

/* ─── Styles ───────────────────────────────────────────────────────────── */

const ls = {
  page: { minHeight: '100vh', color: 'var(--ink)', background: 'transparent' } as React.CSSProperties,
  shell: { display: 'grid', gridTemplateColumns: '260px 1fr', minHeight: '100vh' } as React.CSSProperties,
  sidebar: {
    background: 'rgba(0,0,0,0.30)', borderRight: '1px solid var(--line-2)',
    padding: '20px 16px', display: 'flex', flexDirection: 'column' as const, gap: 6,
    backdropFilter: 'blur(20px)',
  } as React.CSSProperties,
  brand: { display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px 18px', fontWeight: 600, fontSize: 17 } as React.CSSProperties,
  brandMark: {
    width: 30, height: 30, borderRadius: 9, background: 'var(--rainbow)',
    color: 'white', display: 'grid', placeItems: 'center',
    fontFamily: 'var(--font-serif)', fontStyle: 'italic' as const, fontSize: 19,
    boxShadow: '0 2px 14px -2px rgba(244,114,182,0.5)',
  } as React.CSSProperties,
  navItem: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '10px 12px', borderRadius: 10,
    fontSize: 14, color: 'var(--ink-3)', cursor: 'pointer',
    transition: 'background 0.15s ease, color 0.15s ease',
  } as React.CSSProperties,
  navItemActive: { background: 'var(--violet-soft)', color: 'white' } as React.CSSProperties,
  navTag: {
    marginLeft: 'auto', fontSize: 10, fontWeight: 600,
    padding: '2px 7px', borderRadius: 999,
    background: 'var(--violet)', color: 'white',
    letterSpacing: '0.04em', textTransform: 'uppercase' as const,
  } as React.CSSProperties,
  main: { padding: '28px 40px 60px', maxWidth: 1180, width: '100%' } as React.CSSProperties,
  topbar: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 } as React.CSSProperties,
  breadcrumb: { fontSize: 13, color: 'var(--ink-4)', display: 'flex', alignItems: 'center', gap: 8 } as React.CSSProperties,
  userPill: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '6px 6px 6px 14px', borderRadius: 999,
    background: 'var(--surface)', border: '1px solid var(--line)', fontSize: 13,
  } as React.CSSProperties,
  avatar: {
    width: 28, height: 28, borderRadius: '50%',
    background: 'linear-gradient(135deg, #F472B6, #A855F7)',
    display: 'grid', placeItems: 'center', fontWeight: 600, fontSize: 12,
  } as React.CSSProperties,
  hero: {
    background: 'linear-gradient(135deg, rgba(168,85,247,0.18) 0%, rgba(124,58,237,0.10) 50%, rgba(34,211,238,0.10) 100%)',
    border: '1px solid var(--line)', borderRadius: 28,
    padding: '44px 48px', position: 'relative' as const, overflow: 'hidden' as const,
    marginBottom: 28,
  } as React.CSSProperties,
  heroGrid: { display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 40, alignItems: 'center', position: 'relative' as const, zIndex: 2 } as React.CSSProperties,
  newBadge: {
    display: 'inline-flex', alignItems: 'center', gap: 8,
    padding: '6px 12px', borderRadius: 999,
    background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(168,85,247,0.40)',
    fontSize: 12, fontWeight: 600, letterSpacing: '0.04em', color: 'var(--violet-2)',
    textTransform: 'uppercase' as const,
  } as React.CSSProperties,
  h1: {
    fontFamily: 'var(--font-serif)', fontSize: 'clamp(40px, 5vw, 60px)',
    lineHeight: 1, fontWeight: 400, letterSpacing: '-0.02em', margin: '16px 0 14px',
  } as React.CSSProperties,
  sub: { fontSize: 17, lineHeight: 1.5, color: 'var(--ink-2)', maxWidth: 460, margin: '0 0 26px' } as React.CSSProperties,
  ctaRow: { display: 'flex', gap: 10, alignItems: 'center' } as React.CSSProperties,
  primary: {
    display: 'inline-flex', alignItems: 'center', gap: 10,
    padding: '14px 22px', borderRadius: 999,
    background: 'linear-gradient(135deg, var(--violet), var(--violet-deep))',
    color: 'white', fontSize: 15, fontWeight: 500,
    boxShadow: '0 6px 24px -6px rgba(168,85,247,0.6)',
    cursor: 'pointer', border: 'none',
  } as React.CSSProperties,
  ghost: {
    padding: '14px 18px', borderRadius: 999, color: 'var(--ink-2)', fontSize: 14, fontWeight: 500,
    border: '1px solid var(--line)', background: 'var(--surface)', cursor: 'pointer',
  } as React.CSSProperties,
  reassure: { display: 'flex', gap: 18, marginTop: 22, color: 'var(--ink-3)', fontSize: 13 } as React.CSSProperties,
  reItem: { display: 'flex', alignItems: 'center', gap: 6 } as React.CSSProperties,
  threeCol: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 28 } as React.CSSProperties,
  card: {
    background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 20, padding: 22,
    transition: 'border-color 0.2s ease, transform 0.2s ease',
  } as React.CSSProperties,
  stepNum: {
    width: 28, height: 28, borderRadius: 8, display: 'grid', placeItems: 'center',
    fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 500,
  } as React.CSSProperties,
  bottomRow: { display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 16 } as React.CSSProperties,
  bigCard: {
    background: 'linear-gradient(180deg, rgba(168,85,247,0.10), rgba(255,255,255,0.02))',
    border: '1px solid var(--line)', borderRadius: 24, padding: 32,
    position: 'relative' as const, overflow: 'hidden' as const,
  } as React.CSSProperties,
}

/* ─── Sub-components ───────────────────────────────────────────────────── */

function Sidebar() {
  const items = [
    { name: 'Home', icon: 'house' },
    { name: 'Cards', icon: 'wallet' },
    { name: 'Payments', icon: 'send' },
    { name: 'Savings', icon: 'trend-up' },
    { name: 'Stocks', icon: 'spark' },
    { name: 'Crypto', icon: 'sparkles' },
    { name: 'Mortgages', icon: 'key', active: true, tag: 'New' },
    { name: 'Settings', icon: 'shield' },
  ]
  return (
    <aside style={ls.sidebar}>
      <div style={ls.brand}>
        <div style={ls.brandMark}>n</div>
        <span>bunq</span>
      </div>
      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-4)', letterSpacing: '0.08em', textTransform: 'uppercase', padding: '0 12px 8px' }}>
        Personal &middot; Tim de Vries
      </div>
      {items.map((it, i) => (
        <div key={i} style={{ ...ls.navItem, ...(it.active ? ls.navItemActive : {}) }}>
          <Icon name={it.icon} size={17} stroke={it.active ? 2 : 1.6}/>
          <span style={{ fontWeight: it.active ? 500 : 400 }}>{it.name}</span>
          {it.tag && <span style={ls.navTag}>{it.tag}</span>}
        </div>
      ))}
      <div style={{ marginTop: 'auto', padding: 12, borderRadius: 14, background: 'var(--surface)', border: '1px solid var(--line)' }}>
        <div style={{ fontSize: 12, color: 'var(--ink-3)', marginBottom: 4 }}>Total balance</div>
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: 22 }}>&#8364; 38,142.<span style={{ color: 'var(--ink-4)' }}>57</span></div>
        <div style={{ fontSize: 11, color: 'var(--mint)', marginTop: 4 }}>&uarr; &#8364;214 this week</div>
      </div>
    </aside>
  )
}

function MiniHouseScene() {
  return (
    <div style={{ position: 'relative', height: 320, display: 'grid', placeItems: 'center' }}>
      <div style={{
        position: 'absolute', inset: '10%', borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(168,85,247,0.35), transparent 65%)',
        filter: 'blur(30px)',
      }}/>
      <svg width="380" height="300" viewBox="0 0 380 300" style={{ position: 'relative', zIndex: 2 }}>
        <defs>
          <linearGradient id="rg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#C084FC"/><stop offset="1" stopColor="#7C3AED"/>
          </linearGradient>
          <linearGradient id="wg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="rgba(255,255,255,0.10)"/><stop offset="1" stopColor="rgba(255,255,255,0.04)"/>
          </linearGradient>
        </defs>
        <ellipse cx="190" cy="270" rx="160" ry="12" fill="rgba(0,0,0,0.4)"/>
        <path d="M70 140 L70 270 L310 270 L310 140 Z" fill="url(#wg)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
        <path d="M50 145 L190 50 L330 145 L310 145 L190 70 L70 145 Z" fill="url(#rg)"/>
        <rect x="240" y="65" width="20" height="40" fill="#7C3AED"/>
        <rect x="172" y="180" width="44" height="90" rx="4" fill="#22D3EE"/>
        <circle cx="208" cy="225" r="2" fill="white"/>
        <rect x="92" y="160" width="48" height="48" rx="4" fill="rgba(168,85,247,0.20)" stroke="#C084FC" strokeWidth="1.5"/>
        <line x1="116" y1="160" x2="116" y2="208" stroke="#C084FC" strokeWidth="1.5"/>
        <line x1="92" y1="184" x2="140" y2="184" stroke="#C084FC" strokeWidth="1.5"/>
        <rect x="240" y="160" width="48" height="48" rx="4" fill="rgba(168,85,247,0.20)" stroke="#C084FC" strokeWidth="1.5"/>
        <line x1="264" y1="160" x2="264" y2="208" stroke="#C084FC" strokeWidth="1.5"/>
        <line x1="240" y1="184" x2="288" y2="184" stroke="#C084FC" strokeWidth="1.5"/>
        <circle cx="40" cy="40" r="1.5" fill="#C084FC"/>
        <circle cx="350" cy="60" r="2" fill="#22D3EE"/>
        <circle cx="350" cy="20" r="1" fill="white"/>
        <circle cx="20" cy="80" r="1" fill="white"/>
      </svg>
      {/* Floating chat bubble */}
      <div style={{
        position: 'absolute', right: -10, bottom: 20, zIndex: 3,
        background: 'rgba(20,10,32,0.92)', borderRadius: 16, borderBottomRightRadius: 4,
        padding: '12px 16px', border: '1px solid var(--line)',
        backdropFilter: 'blur(12px)', maxWidth: 230, fontSize: 13.5, lineHeight: 1.4,
        animation: 'float-soft 6s ease-in-out infinite',
        boxShadow: '0 12px 40px -12px rgba(0,0,0,0.6)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <div style={{
            width: 22, height: 22, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--violet), var(--violet-deep))',
            display: 'grid', placeItems: 'center', color: 'white',
          }}><Icon name="bunq" size={14} stroke={2}/></div>
          <span style={{ fontSize: 11, color: 'var(--ink-3)', fontWeight: 500 }}>Nest coach</span>
        </div>
        <span style={{ color: 'var(--ink-2)' }}>Save &#8364;420/mo for 14 months — and you're there.</span>
      </div>
      {/* Floating borrow pill */}
      <div style={{
        position: 'absolute', left: 0, top: 30, zIndex: 3,
        background: 'rgba(255,255,255,0.06)', color: 'white',
        padding: '8px 12px', borderRadius: 14,
        border: '1px solid var(--line)', backdropFilter: 'blur(12px)',
        animation: 'float-soft 7s ease-in-out infinite 0.5s',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{ width: 32, height: 32, borderRadius: 10, background: 'var(--violet-soft)', color: 'var(--violet-2)', display: 'grid', placeItems: 'center' }}>
          <Icon name="trend-up" size={16}/>
        </div>
        <div>
          <div style={{ fontSize: 10, color: 'var(--ink-4)' }}>You can borrow</div>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: 18, lineHeight: 1 }}>&#8364;384,500</div>
        </div>
      </div>
    </div>
  )
}

function Steps() {
  const steps = [
    { n: '01', icon: 'upload', t: 'Drop your payslip', d: 'Snap or upload your latest. Nest reads the income for you.', c: '#F472B6', bg: 'rgba(244,114,182,0.14)' },
    { n: '02', icon: 'link', t: 'Paste a Funda link', d: 'Found a place you love? Paste the link — we\'ll fetch the asking price.', c: '#22D3EE', bg: 'rgba(34,211,238,0.14)' },
    { n: '03', icon: 'chat', t: 'Chat with your coach', d: 'Claude walks you through what\'s actually possible — clearly, honestly.', c: '#C084FC', bg: 'rgba(168,85,247,0.16)' },
  ]
  return (
    <div style={ls.threeCol}>
      {steps.map((s, i) => (
        <div key={i} style={ls.card}
             onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = s.c + '66' }}
             onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--line)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 12, background: s.bg, color: s.c,
              display: 'grid', placeItems: 'center', border: `1px solid ${s.c}33`,
            }}>
              <Icon name={s.icon} size={22} stroke={1.7}/>
            </div>
            <span style={{ ...ls.stepNum, background: s.bg, color: s.c }}>{s.n}</span>
          </div>
          <div style={{ fontSize: 18, fontWeight: 500, marginBottom: 6, letterSpacing: '-0.01em' }}>{s.t}</div>
          <div style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--ink-3)' }}>{s.d}</div>
        </div>
      ))}
    </div>
  )
}

function Capability({ icon, label, sub, c = 'var(--violet-2)', bg = 'var(--violet-soft)' }: { icon: string; label: string; sub: string; c?: string; bg?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{ width: 36, height: 36, borderRadius: 10, background: bg, color: c, display: 'grid', placeItems: 'center' }}>
        <Icon name={icon} size={18}/>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 500 }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--ink-4)' }}>{sub}</div>
      </div>
      <Icon name="check" size={14} color="var(--mint)"/>
    </div>
  )
}

/* ─── Main export ──────────────────────────────────────────────────────── */

export function WelcomeRoute() {
  const navigate  = useNavigate()
  const { search } = useLocation()

  function handleStart() { navigate(`/onboard${search}`) }

  return (
    <div style={ls.page}>
      <div style={ls.shell}>
        <Sidebar />
        <div style={ls.main}>
          {/* Top bar */}
          <div style={ls.topbar}>
            <div style={ls.breadcrumb}>
              <span>bunq</span>
              <Icon name="arrow-right" size={12}/>
              <span style={{ color: 'white' }}>Mortgages</span>
            </div>
            <div style={ls.userPill}>
              <span>Tim de Vries</span>
              <div style={ls.avatar}>TV</div>
            </div>
          </div>

          {/* Hero */}
          <section style={ls.hero}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: 'var(--rainbow)', opacity: 0.85 }}/>
            <div style={{ position: 'absolute', top: -60, right: -60, width: 240, height: 240, borderRadius: '50%', background: 'radial-gradient(circle, rgba(168,85,247,0.4), transparent 60%)', filter: 'blur(20px)' }}/>
            <div style={{ position: 'absolute', bottom: -40, left: 100, width: 200, height: 200, borderRadius: '50%', background: 'radial-gradient(circle, rgba(244,114,182,0.16), transparent 60%)', filter: 'blur(20px)' }}/>
            <div style={ls.heroGrid}>
              <div className="animate-fade-up">
                <div style={ls.newBadge}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--violet-2)', display: 'inline-block' }}/>
                  New in bunq &middot; Mortgages
                </div>
                <h1 style={ls.h1}>
                  See if you can<br/>
                  <span style={{ fontStyle: 'italic', color: 'var(--violet-2)' }}>afford that home.</span>
                </h1>
                <p style={ls.sub}>
                  Drop a Funda link and your latest payslip. We'll show your borrowing power, the gap, and the fastest path to close it. Right here in your bunq.
                </p>
                <div style={ls.ctaRow}>
                  <button onClick={handleStart} style={ls.primary}>
                    Start a check <Icon name="arrow-right" size={18}/>
                  </button>
                  <button style={ls.ghost}>How it works</button>
                </div>
                <div style={ls.reassure}>
                  <div style={ls.reItem}><Icon name="check" size={14} color="var(--mint)"/> 2 min &middot; no credit check</div>
                  <div style={ls.reItem}><Icon name="check" size={14} color="var(--mint)"/> Uses your bunq data</div>
                </div>
              </div>
              <div className="animate-fade-up" style={{ animationDelay: '0.15s' }}>
                <MiniHouseScene />
              </div>
            </div>
          </section>

          {/* Steps */}
          <Steps />

          {/* Bottom row */}
          <div style={ls.bottomRow}>
            <div style={ls.bigCard}>
              <div style={{ position: 'absolute', top: -30, right: -30, width: 200, height: 200, borderRadius: '50%', background: 'radial-gradient(circle, rgba(168,85,247,0.30), transparent 60%)', filter: 'blur(10px)' }}/>
              <div style={{ position: 'relative', maxWidth: 480 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--violet-2)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 12 }}>
                  Why we built it
                </div>
                <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 38, margin: '0 0 14px', fontWeight: 400, letterSpacing: '-0.02em', lineHeight: 1.05 }}>
                  Mortgages without the <span style={{ fontStyle: 'italic', color: 'var(--violet-2)' }}>knot in your stomach.</span>
                </h2>
                <p style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--ink-3)', marginBottom: 22 }}>
                  You shouldn't need a financial advisor and a spreadsheet to find out if you can afford a home. Nest lives inside your bunq, knows your numbers, and tells you the truth in plain language.
                </p>
                <button onClick={handleStart} style={ls.primary}>
                  Try it on a home you love <Icon name="arrow-right" size={16}/>
                </button>
              </div>
            </div>
            <div style={{ ...ls.card, padding: 24 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-4)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 14 }}>
                Already in your bunq
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <Capability icon="wallet" label="Income & spending" sub="From your last 12 months" c="#F472B6" bg="rgba(244,114,182,0.14)"/>
                <Capability icon="trend-up" label="Savings & goals" sub="Live from your accounts" c="#34D399" bg="rgba(52,211,153,0.14)"/>
                <Capability icon="shield" label="Verified identity" sub="No re-KYC needed" c="#22D3EE" bg="rgba(34,211,238,0.14)"/>
                <Capability icon="sparkles" label="Claude Sonnet" sub="Powering the coach" c="#C084FC" bg="rgba(168,85,247,0.16)"/>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
