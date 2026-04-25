import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { ChatView } from '@/chat/ChatView'
import { DisclaimerBanner } from '@/shell/DisclaimerBanner'
import { HandoffCTAConnected } from '@/shell/HandoffCTA'
import { useChatStore } from '@/chat/chatStore'
import type { ProfileSnapshot } from '@/api/types'

export function ChatRoute() {
  const { state } = useLocation()
  const setProfile = useChatStore((s) => s.setProfile)

  // Profile arrives via navigate state from OnboardForm on first session.
  // On session resume it would come from GET /chat/sessions/{id} (TODO).
  useEffect(() => {
    const profile = (state as { profile?: ProfileSnapshot } | null)?.profile
    if (profile) setProfile(profile)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex flex-col h-screen">
      <DisclaimerBanner />
      <ChatView />
      <HandoffCTAConnected />
    </div>
  )
}
