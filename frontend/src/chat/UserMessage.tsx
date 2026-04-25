type Props = { content: string }

export function UserMessage({ content }: Props) {
  return (
    <div className="animate-fade-up" style={{ display: 'flex', justifyContent: 'flex-end' }}>
      <div style={{
        maxWidth: 560,
        padding: '14px 18px',
        background: 'linear-gradient(135deg, var(--violet), var(--violet-deep))',
        color: 'white',
        borderRadius: 18, borderTopRightRadius: 6,
        fontSize: 15, lineHeight: 1.55,
      }}>
        {content}
      </div>
    </div>
  )
}
