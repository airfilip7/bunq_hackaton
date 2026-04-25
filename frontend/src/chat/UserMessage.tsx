type Props = { content: string }

export function UserMessage({ content }: Props) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '0 16px' }}>
      <div style={{
        maxWidth: '78%',
        background: 'var(--surface-2)',
        border: '1px solid var(--surface-3)',
        borderRadius: '16px 16px 4px 16px',
        padding: '10px 14px',
        fontSize: 14,
        lineHeight: 1.5,
        color: 'var(--text-primary)',
      }}>
        {content}
      </div>
    </div>
  )
}
