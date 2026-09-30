const recentErrors = new Map<string, number>()
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

type ErrorContext = {
  kind: string
  method?: string
  path?: string
  status?: number
}

function errorDetails(error: unknown) {
  if (error instanceof Error) return { message: error.message, stack: error.stack ?? '' }
  return { message: String(error || 'Unknown frontend error'), stack: '' }
}

export function reportFrontendError(error: unknown, context: ErrorContext) {
  const { message, stack } = errorDetails(error)
  const fingerprint = `${context.kind}:${context.method ?? ''}:${context.path ?? ''}:${message}`
  const now = Date.now()
  if ((recentErrors.get(fingerprint) ?? 0) > now - 10_000) return
  recentErrors.set(fingerprint, now)

  const report = JSON.stringify({
    message: message.slice(0, 2_000),
    stack: stack.slice(0, 8_000),
    context,
  })

  // Telemetry contains only failure metadata.  It never sends form values,
  // request bodies, cookies, or authentication data.
  void fetch(`${API_BASE_URL}/api/telemetry/client-errors/`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: report,
    keepalive: true,
  }).catch(() => undefined)

  if (import.meta.env.DEV) {
    console.error('[registry frontend]', { ...context, message, stack })
  }
}
