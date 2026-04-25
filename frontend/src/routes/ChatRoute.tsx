import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { ChatView } from '@/chat/ChatView'
import { useChatStore } from '@/chat/chatStore'
import type { ProfileSnapshot } from '@/api/types'

export function ChatRoute() {
  const { state } = useLocation()
  const setProfile = useChatStore((s) => s.setProfile)

  useEffect(() => {
    const profile = (state as { profile?: ProfileSnapshot } | null)?.profile
    if (profile) setProfile(profile)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return <ChatView />
}
