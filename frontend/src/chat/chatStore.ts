import { create } from 'zustand'
import type { Message, ToolProposal, ProfileSnapshot } from '@/api/types'

export type StreamState = 'idle' | 'streaming' | 'awaiting_approval' | 'error'

type ChatStore = {
  sessionId: string | null
  messages: Message[]
  pendingTool: ToolProposal | null
  streamState: StreamState
  errorMessage: string | null
  profile: ProfileSnapshot | null

  // actions
  setSession: (id: string) => void
  setProfile: (profile: ProfileSnapshot) => void
  appendUserMessage: (msg: Message) => void
  startAssistantMessage: (id: string) => void
  appendDelta: (id: string, text: string) => void
  finaliseAssistantMessage: (id: string) => void
  setToolResult: (tool_use_id: string, ok: boolean, summary?: string, error?: string) => void
  setPendingTool: (proposal: ToolProposal | null) => void
  setStreamState: (state: StreamState) => void
  setError: (msg: string | null) => void
  reset: () => void
}

const initialState = {
  sessionId: null,
  messages: [],
  pendingTool: null,
  streamState: 'idle' as StreamState,
  errorMessage: null,
  profile: null,
}

export const useChatStore = create<ChatStore>((set) => ({
  ...initialState,

  setSession: (id) => set({ sessionId: id }),

  setProfile: (profile) => set({ profile }),

  appendUserMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  startAssistantMessage: (id) =>
    set((s) => ({
      messages: [
        ...s.messages,
        { id, role: 'assistant', content: '', streaming: true, tool_calls: [] },
      ],
    })),

  appendDelta: (id, text) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + text } : m,
      ),
    })),

  finaliseAssistantMessage: (id) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, streaming: false } : m,
      ),
    })),

  // Attaches a tool_result to the most recent assistant message's tool_calls.
  setToolResult: (tool_use_id, ok, summary, error) =>
    set((s) => {
      const messages = [...s.messages]
      const last = messages.findLast((m) => m.role === 'assistant')
      if (!last) return {}
      const tool_calls = (last.tool_calls ?? []).map((tc) =>
        tc.tool_use_id === tool_use_id ? { ...tc, result: { ok, summary, error } } : tc,
      )
      return {
        messages: messages.map((m) => (m.id === last.id ? { ...m, tool_calls } : m)),
      }
    }),

  setPendingTool: (proposal) => set({ pendingTool: proposal }),

  setStreamState: (state) => set({ streamState: state }),

  setError: (msg) => set({ errorMessage: msg }),

  reset: () => set(initialState),
}))
