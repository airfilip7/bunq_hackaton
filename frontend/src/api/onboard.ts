import { apiFetch } from './client'
import type { OnboardRequest, UploadUrlResponse, OnboardResponse } from './types'

export async function getUploadUrl(): Promise<UploadUrlResponse> {
  const res = await apiFetch('/onboard/upload-url', { method: 'POST' })
  if (!res.ok) throw new Error('Failed to get upload URL')
  return res.json() as Promise<UploadUrlResponse>
}

export async function uploadPayslip(file: File, uploadData: UploadUrlResponse): Promise<void> {
  const res = await fetch(uploadData.upload_url, {
    method: 'PUT',
    headers: uploadData.required_headers,
    body: file,
  })
  if (!res.ok) throw new Error('Payslip upload failed')
}

export async function submitOnboard(body: OnboardRequest): Promise<OnboardResponse> {
  const res = await apiFetch('/onboard', { method: 'POST', body: JSON.stringify(body) })
  if (!res.ok) throw new Error('Onboard submission failed')
  return res.json() as Promise<OnboardResponse>
}
