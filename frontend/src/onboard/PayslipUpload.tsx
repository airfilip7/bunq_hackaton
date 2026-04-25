import { useRef, useState } from 'react'
import { getUploadUrl, uploadPayslip } from '@/api/onboard'

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']
const MAX_BYTES = 10 * 1024 * 1024

function validate(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) return 'Please upload a JPG, PNG, or WebP image.'
  if (file.size > MAX_BYTES) return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max 10 MB.`
  return null
}

type Props = { onComplete: (s3Key: string) => void }

export function PayslipUpload({ onComplete }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [status, setStatus]     = useState<'idle' | 'uploading' | 'done' | 'error'>('idle')
  const [fileName, setFileName] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [hovering, setHovering] = useState(false)

  async function handleFile(file: File) {
    const err = validate(file)
    if (err) { setErrorMsg(err); setStatus('error'); return }
    setFileName(file.name)
    setErrorMsg(null)
    setStatus('uploading')
    try {
      const uploadData = await getUploadUrl()
      await uploadPayslip(file, uploadData)
      setStatus('done')
      onComplete(uploadData.s3_key)
    } catch (err) {
      console.error('[PayslipUpload]', err)
      setErrorMsg('Upload failed — please try again.')
      setStatus('error')
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ''
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setHovering(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  /* ── Done state — file parsed ── */
  if (status === 'done' && fileName) {
    return (
      <div style={{
        background: 'var(--surface-2)', border: '1px solid var(--surface-3)',
        borderRadius: 14, padding: 14,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{
          width: 40, height: 48, borderRadius: 6, flexShrink: 0,
          background: 'rgba(30,200,200,0.1)', border: '1px solid rgba(30,200,200,0.3)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--bunq-teal)',
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6M9 13h6M9 17h4" />
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {fileName}
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--success)', marginTop: 3, display: 'flex', alignItems: 'center', gap: 5 }}>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <circle cx="5" cy="5" r="4" fill="currentColor" opacity="0.18" />
              <path d="M3 5L4.5 6.5L7.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Uploaded successfully
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); setStatus('idle'); setFileName(null) }}
          style={{
            width: 30, height: 30, borderRadius: 8, flexShrink: 0,
            background: 'transparent', border: '1px solid var(--surface-3)',
            color: 'var(--text-secondary)', cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M3 3L9 9M9 3L3 9" />
          </svg>
        </button>
      </div>
    )
  }

  /* ── Drop zone ── */
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setHovering(true) }}
      onDragLeave={() => setHovering(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      style={{
        position: 'relative',
        background: hovering ? 'rgba(30,200,200,0.06)' : 'var(--surface-2)',
        border: `1.5px dashed ${hovering ? 'var(--bunq-teal)' : 'rgba(30,200,200,0.45)'}`,
        borderRadius: 14,
        padding: '26px 18px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
        cursor: 'pointer',
        transition: 'background 120ms ease, border-color 120ms ease',
      }}
    >
      <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleChange} />

      <div style={{
        width: 44, height: 44, borderRadius: 12,
        background: 'rgba(30,200,200,0.1)',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--bunq-teal)',
      }}>
        {status === 'uploading'
          ? <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'spin 1s linear infinite' }}><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" /></svg>
          : <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
        }
      </div>

      <div style={{ textAlign: 'center' }}>
        {status === 'uploading'
          ? <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--bunq-teal)' }}>Uploading {fileName}…</div>
          : status === 'error'
          ? <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--error)' }}>{errorMsg}</div>
          : <>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>Drop your payslip here</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3 }}>
                or <span style={{ color: 'var(--bunq-teal)', fontWeight: 500 }}>browse files</span> · JPG, PNG, WebP
              </div>
            </>
        }
      </div>

      {status === 'error' && (
        <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); setStatus('idle'); setErrorMsg(null) }}>
          Try again
        </button>
      )}

      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 10.5, color: 'var(--text-disabled)', marginTop: 2 }}>
        <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
          <path d="M9.5 5.5V4a3.5 3.5 0 0 0-7 0v1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" fill="none" />
          <rect x="2" y="5.5" width="8" height="5.5" rx="1.2" stroke="currentColor" strokeWidth="1.2" fill="none" />
        </svg>
        Bank-grade encryption · we never store originals
      </div>
    </div>
  )
}
