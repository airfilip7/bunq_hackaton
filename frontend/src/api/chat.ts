import { apiFetch } from './client'
import type { TurnRequest } from './types'

export async function postTurn(sessionId: string, body: TurnRequest): Promise<Response> {
  return apiFetch(`/chat/sessions/${sessionId}/turns`, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { Accept: 'text/event-stream' },
  })
}

export async function getSessions(): Promise<Response> {
  return apiFetch('/chat/sessions')
}

export async function getSession(sessionId: string): Promise<Response> {
  return apiFetch(`/chat/sessions/${sessionId}`)
}
