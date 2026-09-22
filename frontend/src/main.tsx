import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { reportFrontendError } from './error-reporting.ts'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
)

window.addEventListener('error', (event) => {
  reportFrontendError(event.error ?? event.message, { kind: 'window-error', path: window.location.pathname })
})
window.addEventListener('unhandledrejection', (event) => {
  reportFrontendError(event.reason, { kind: 'unhandled-rejection', path: window.location.pathname })
})
