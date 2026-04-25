import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { OnboardRoute } from './routes/OnboardRoute'
import { ChatRoute }    from './routes/ChatRoute'

const queryClient = new QueryClient()

// Redirect that keeps ?mock=1 / ?demo=1 alive across navigation.
function PreserveParamsRedirect({ to }: { to: string }) {
  const { search } = useLocation()
  return <Navigate to={`${to}${search}`} replace />
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/onboard" element={<OnboardRoute />} />
          <Route path="/chat"    element={<ChatRoute />} />
          <Route path="*"        element={<PreserveParamsRedirect to="/onboard" />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
