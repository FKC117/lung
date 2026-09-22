import { Component, type ErrorInfo, type ReactNode } from 'react'
import { reportFrontendError } from '../error-reporting'

type Props = { children: ReactNode }
type State = { hasError: boolean }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    reportFrontendError(error, { kind: 'react-render', path: window.location.pathname })
    reportFrontendError(info.componentStack || 'React component stack unavailable', { kind: 'react-component-stack' })
  }

  render() {
    if (this.state.hasError) {
      return <section className="panel state-card"><h2>Something went wrong</h2><p>The error was recorded. Please refresh the page and try again.</p></section>
    }
    return this.props.children
  }
}
