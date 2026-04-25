import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { OnboardRoute }      from './routes/OnboardRoute'
import { ChatRoute }         from './routes/ChatRoute'
import { AuthCallbackRoute } from './routes/AuthCallbackRoute'

const queryClient = new QueryClient()

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/onboard"       element={<OnboardRoute />} />
          <Route path="/chat"          element={<ChatRoute />} />
          <Route path="/auth/callback" element={<AuthCallbackRoute />} />
          <Route path="*"              element={<Navigate to="/onboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
