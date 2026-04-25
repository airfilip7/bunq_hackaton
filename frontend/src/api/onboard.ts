import { apiFetch } from './client'
import type { OnboardRequest, OnboardResponse, FundaParseResult, PayslipUploadResult } from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export async function uploadPayslip(file: File): Promise<PayslipUploadResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/onboard/upload-payslip`, {
    method: 'POST',
    headers: {
      'X-Dev-User-Id': 'u_demo',
      'Authorization': 'Bearer demo',
    },
    body: form,
  })
  if (!res.ok) throw new Error('Payslip upload failed')
  return res.json() as Promise<PayslipUploadResult>
}

export async function parseFunda(url: string): Promise<FundaParseResult> {
  const res = await apiFetch('/onboard/parse-funda', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
  if (!res.ok) throw new Error(`parse-funda ${res.status}`)
  return res.json() as Promise<FundaParseResult>
}

export async function submitOnboard(body: OnboardRequest): Promise<OnboardResponse> {
  const res = await apiFetch('/onboard', { method: 'POST', body: JSON.stringify(body) })
  if (!res.ok) throw new Error('Onboard submission failed')
  return res.json() as Promise<OnboardResponse>
}
