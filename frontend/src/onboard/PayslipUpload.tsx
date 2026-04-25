import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { getUploadUrl, uploadPayslip } from '@/api/onboard'

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']
const MAX_BYTES = 10 * 1024 * 1024  // 10 MB

function validate(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type))
    return 'Please upload a JPG, PNG, or WebP image.'
  if (file.size > MAX_BYTES)
    return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max 10 MB.`
  return null
}

type Props = {
  onComplete: (s3Key: string) => void
}

export function PayslipUpload({ onComplete }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [status, setStatus]     = useState<'idle' | 'uploading' | 'done' | 'error'>('idle')
  const [fileName, setFileName] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  async function handleFile(file: File) {
    const validationError = validate(file)
    if (validationError) {
      setErrorMsg(validationError)
      setStatus('error')
      return
    }
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
    // Reset input so the same file can be re-selected after an error.
    e.target.value = ''
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className="border-2 border-dashed border-surface-3 rounded-xl p-8 flex flex-col items-center gap-4 cursor-pointer hover:border-bunq-teal/50 transition-colors"
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleChange}
      />

      <div className="text-4xl">📄</div>

      {status === 'idle' && (
        <>
          <p className="text-text-primary font-medium">Upload your payslip (loonstrook)</p>
          <p className="text-text-secondary text-sm">Drag and drop or click to select · JPG, PNG</p>
        </>
      )}

      {status === 'uploading' && (
        <p className="text-bunq-teal text-sm animate-pulse">Uploading {fileName}…</p>
      )}

      {status === 'done' && (
        <p className="text-bunq-teal text-sm">✓ {fileName} uploaded</p>
      )}

      {status === 'error' && (
        <>
          <p className="text-error text-sm">{errorMsg}</p>
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => { e.stopPropagation(); setStatus('idle'); setErrorMsg(null) }}
          >
            Try again
          </Button>
        </>
      )}
    </div>
  )
}
