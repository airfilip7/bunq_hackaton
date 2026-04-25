type IconProps = {
  name: string
  size?: number
  stroke?: number
  color?: string
  style?: React.CSSProperties
}

export function Icon({ name, size = 20, stroke = 1.6, color = 'currentColor', style = {}, ...rest }: IconProps) {
  const props = {
    width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
    stroke: color, strokeWidth: stroke, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const,
    style, ...rest,
  }
  switch (name) {
    case 'house':
      return <svg {...props}><path d="M3 11.5 12 4l9 7.5"/><path d="M5 10.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9.5"/></svg>
    case 'leaf':
      return <svg {...props}><path d="M5 19c0-9 6-15 15-15 0 9-6 15-15 15Z"/><path d="M5 19c4-4 8-7 11-9"/></svg>
    case 'spark':
      return <svg {...props}><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></svg>
    case 'shield':
      return <svg {...props}><path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z"/><path d="m9 12 2 2 4-4"/></svg>
    case 'chat':
      return <svg {...props}><path d="M21 12a8 8 0 1 1-3.2-6.4L21 4l-1 4.2A8 8 0 0 1 21 12Z"/><path d="M8.5 12h.01M12 12h.01M15.5 12h.01"/></svg>
    case 'upload':
      return <svg {...props}><path d="M12 16V4M7 9l5-5 5 5"/><path d="M5 16v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3"/></svg>
    case 'image':
      return <svg {...props}><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m3 17 5-4 5 4 3-3 5 4"/></svg>
    case 'link':
      return <svg {...props}><path d="M10 14a4 4 0 0 1 0-5.6l3-3a4 4 0 0 1 5.6 5.6l-1.5 1.5"/><path d="M14 10a4 4 0 0 1 0 5.6l-3 3a4 4 0 0 1-5.6-5.6L7 11.5"/></svg>
    case 'check':
      return <svg {...props}><path d="m5 12 5 5 9-11"/></svg>
    case 'arrow-right':
      return <svg {...props}><path d="M5 12h14M13 6l6 6-6 6"/></svg>
    case 'arrow-left':
      return <svg {...props}><path d="M19 12H5M11 6l-6 6 6 6"/></svg>
    case 'send':
      return <svg {...props}><path d="m4 12 16-8-6 18-3-7-7-3Z"/></svg>
    case 'sparkles':
      return <svg {...props}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2 2M16 16l2 2M6 18l2-2M16 8l2-2"/></svg>
    case 'wallet':
      return <svg {...props}><path d="M3 7h15a3 3 0 0 1 3 3v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/><path d="M3 7V6a2 2 0 0 1 2-2h11"/><circle cx="17" cy="13" r="1.2" fill="currentColor"/></svg>
    case 'trend-up':
      return <svg {...props}><path d="m3 17 6-6 4 4 8-9"/><path d="M14 6h7v7"/></svg>
    case 'calendar':
      return <svg {...props}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>
    case 'key':
      return <svg {...props}><circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M16 7l3 3M14 9l3 3"/></svg>
    case 'x':
      return <svg {...props}><path d="m6 6 12 12M18 6 6 18"/></svg>
    case 'plus':
      return <svg {...props}><path d="M12 5v14M5 12h14"/></svg>
    case 'info':
      return <svg {...props}><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/></svg>
    case 'heart':
      return <svg {...props}><path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.7A4 4 0 0 1 19 10c0 5.5-7 10-7 10Z"/></svg>
    case 'loader':
      return <svg {...props} style={{ animation: 'spin 1s linear infinite', ...style }}><path d="M12 3v3M12 18v3M21 12h-3M6 12H3M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1M18.4 18.4l-2.1-2.1M7.7 7.7 5.6 5.6"/></svg>
    case 'doc':
      return <svg {...props}><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z"/><path d="M14 3v6h6M8 13h8M8 17h5"/></svg>
    case 'camera':
      return <svg {...props}><path d="M4 8h3l2-2h6l2 2h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2Z"/><circle cx="12" cy="13" r="3.5"/></svg>
    case 'pin':
      return <svg {...props}><path d="M12 22s-7-7.5-7-13a7 7 0 0 1 14 0c0 5.5-7 13-7 13Z"/><circle cx="12" cy="9" r="2.5"/></svg>
    case 'bunq':
      return (
        <svg {...props} viewBox="0 0 24 24">
          <path d="M5 14c0-3.3 3.1-6 7-6s7 2.7 7 6c0 1.6-1 3-3 3"/>
          <path d="M9 13c0-1 1-2 3-2s3 1 3 2"/>
        </svg>
      )
    default: return null
  }
}
