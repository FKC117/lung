const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const recentErrors = new Map<string, number>()

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

  // LEGACY_API: this frontend used to send errors to an endpoint that the
  // current backend deliberately does not expose. Keep errors local instead.
  if (import.meta.env.DEV) {
    console.error('[registry frontend]', { ...context, message, stack })
  }
}
