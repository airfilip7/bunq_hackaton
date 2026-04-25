import { useRef, useState } from 'react'
import { Icon } from '@/components/Icon'
import { uploadPayslip } from '@/api/onboard'
import type { PayslipUploadResult } from '@/api/types'

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']
const MAX_BYTES = 10 * 1024 * 1024

function validate(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) return 'Please upload a JPG, PNG, or WebP image.'
  if (file.size > MAX_BYTES) return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max 10 MB.`
  return null
}

type Props = { onComplete: (result: PayslipUploadResult) => void }

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
      const result = await uploadPayslip(file)
      setStatus('done')
      onComplete(result)
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

  /* ── Done state ── */
  if (status === 'done' && fileName) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14,
        background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)',
        borderRadius: 14, padding: '12px 14px',
      }}>
        <div style={{
          width: 40, height: 52, borderRadius: 8,
          background: 'linear-gradient(135deg, rgba(168,85,247,0.30), rgba(124,58,237,0.20))',
          display: 'grid', placeItems: 'center', color: 'var(--violet-2)',
          border: '1px solid var(--line)', flexShrink: 0,
        }}>
          <Icon name="doc" size={18} stroke={1.5}/>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {fileName}
          </div>
          <div style={{ fontSize: 12, color: 'var(--violet-2)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="check" size={13} color="var(--violet-2)"/>
            Read successfully
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); setStatus('idle'); setFileName(null) }}
          style={{ width: 28, height: 28, borderRadius: 8, color: 'var(--ink-4)', display: 'grid', placeItems: 'center', cursor: 'pointer' }}
        >
          <Icon name="x" size={16}/>
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
        border: `2px dashed ${hovering ? 'var(--violet)' : 'var(--line)'}`,
        borderRadius: 18,
        padding: '26px 20px',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        background: hovering ? 'var(--violet-soft)' : 'rgba(168,85,247,0.05)',
        cursor: 'pointer',
        transition: 'border-color 0.15s ease, background 0.15s ease',
      }}
    >
      <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleChange} />

      <div style={{
        width: 50, height: 50, borderRadius: 14,
        background: 'var(--violet-soft)', color: 'var(--violet-2)',
        display: 'grid', placeItems: 'center',
        border: '1px solid rgba(168,85,247,0.3)', marginBottom: 12,
      }}>
        {status === 'uploading'
          ? <Icon name="loader" size={22} stroke={1.7}/>
          : <Icon name="upload" size={22} stroke={1.7}/>
        }
      </div>

      {status === 'uploading' ? (
        <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--violet-2)' }}>Reading payslip...</div>
      ) : status === 'error' ? (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--terracotta)', marginBottom: 8 }}>{errorMsg}</div>
          <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); setStatus('idle'); setErrorMsg(null) }}>
            Try again
          </button>
        </div>
      ) : (
        <>
          <div style={{ fontSize: 15, fontWeight: 500, color: 'white', marginBottom: 4 }}>Drop payslip here, or click to upload</div>
          <div style={{ fontSize: 12, color: 'var(--ink-4)' }}>PDF, JPG, PNG &middot; up to 10 MB</div>
          <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
            <button style={{
              background: 'rgba(255,255,255,0.05)', border: '1px solid var(--line)',
              padding: '8px 14px', borderRadius: 999, fontSize: 13, fontWeight: 500,
              display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--ink-2)', cursor: 'pointer',
            }}>
              <Icon name="camera" size={14}/> Take a photo
            </button>
          </div>
        </>
      )}
    </div>
  )
}
