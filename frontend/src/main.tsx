import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { App } from './App'

async function enableMocking() {
  // MSW is active when ?mock=1 or ?demo=1 is in the URL.
  const params = new URLSearchParams(window.location.search)
  if (!params.has('mock') && !params.has('demo')) return
  const { worker } = await import('./mocks/browser')
  return worker.start({ onUnhandledRequest: 'bypass' })
}

enableMocking().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
