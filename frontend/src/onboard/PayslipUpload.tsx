import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { getUploadUrl, uploadPayslip } from '@/api/onboard'

type Props = {
  onComplete: (s3Key: string) => void
}

export function PayslipUpload({ onComplete }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [status, setStatus]   = useState<'idle' | 'uploading' | 'done' | 'error'>('idle')
  const [fileName, setFileName] = useState<string | null>(null)

  async function handleFile(file: File) {
    setFileName(file.name)
    setStatus('uploading')
    try {
      const uploadData = await getUploadUrl()
      await uploadPayslip(file, uploadData)
      setStatus('done')
      onComplete(uploadData.s3_key)
    } catch {
      setStatus('error')
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
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
          <p className="text-error text-sm">Upload failed — try again</p>
          <Button size="sm" variant="ghost" onClick={() => setStatus('idle')}>Retry</Button>
        </>
      )}
    </div>
  )
}
