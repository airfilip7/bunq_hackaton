import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'

const components: Components = {
  p: ({ children }) => <p style={{ margin: '0 0 8px' }}>{children}</p>,
  strong: ({ children }) => (
    <strong style={{ color: 'var(--yellow)', fontWeight: 600 }}>{children}</strong>
  ),
  em: ({ children }) => <em style={{ fontStyle: 'italic', opacity: 0.9 }}>{children}</em>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer" style={{ color: 'var(--teal)', textDecoration: 'underline' }}>
      {children}
    </a>
  ),
  code: ({ children }) => (
    <code style={{
      background: 'rgba(255,255,255,0.08)',
      padding: '2px 5px',
      borderRadius: 4,
      fontFamily: 'monospace',
      fontSize: '0.92em',
    }}>{children}</code>
  ),
  pre: ({ children }) => (
    <pre style={{
      background: 'rgba(0,0,0,0.35)',
      padding: '10px 14px',
      borderRadius: 8,
      overflowX: 'auto',
      fontFamily: 'monospace',
      fontSize: '0.85em',
      margin: '8px 0',
    }}>{children}</pre>
  ),
  ul: ({ children }) => <ul style={{ paddingLeft: 20, margin: '6px 0' }}>{children}</ul>,
  ol: ({ children }) => <ol style={{ paddingLeft: 20, margin: '6px 0' }}>{children}</ol>,
  li: ({ children }) => <li style={{ margin: '3px 0' }}>{children}</li>,
  h1: ({ children }) => <h1 style={{ fontSize: 18, fontWeight: 700, margin: '12px 0 6px' }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ fontSize: 16, fontWeight: 700, margin: '10px 0 6px' }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ fontSize: 15, fontWeight: 600, margin: '8px 0 4px' }}>{children}</h3>,
  blockquote: ({ children }) => (
    <blockquote style={{
      borderLeft: '3px solid var(--teal)',
      paddingLeft: 12,
      margin: '8px 0',
      opacity: 0.85,
    }}>{children}</blockquote>
  ),
  hr: () => <hr style={{ border: 'none', borderTop: '1px solid var(--line)', margin: '10px 0' }} />,
}

export function Markdown({ text }: { text: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {text}
    </ReactMarkdown>
  )
}
