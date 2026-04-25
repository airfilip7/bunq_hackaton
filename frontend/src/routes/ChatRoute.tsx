import { ChatView } from '@/chat/ChatView'
import { DisclaimerBanner } from '@/shell/DisclaimerBanner'
import { HandoffCTAConnected } from '@/shell/HandoffCTA'

export function ChatRoute() {
  return (
    <div className="flex flex-col h-screen">
      <DisclaimerBanner />
      <ChatView />
      <HandoffCTAConnected />
    </div>
  )
}
