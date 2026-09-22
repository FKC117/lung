// LEGACY_UI: role selection belongs to the retired SPA auth API; Django Admin owns authentication.
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { ApiError, loginUser, type AuthUser } from '../api'

function routeUser(user: AuthUser, fallbackPath?: string) {
  if (fallbackPath && fallbackPath !== '/login') {
    if (fallbackPath.startsWith('/admin')) {
      window.location.assign(fallbackPath)
      return
    }
    window.location.assign(fallbackPath)
    return
  }

  if (user.default_redirect.startsWith('/admin')) {
    window.location.assign(user.default_redirect)
    return
  }

  window.location.assign(user.default_redirect)
}

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'admin' | 'doctor' | 'user'>('doctor')
  const [errorMessage, setErrorMessage] = useState('')
  const location = useLocation()
  const queryClient = useQueryClient()
  const redirectTo =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname

  const loginMutation = useMutation({
    mutationFn: ({
      username,
      password,
      role,
    }: {
      username: string
      password: string
      role: 'admin' | 'doctor' | 'user'
    }) => loginUser(username, password, role),
    onSuccess: async (user) => {
      setErrorMessage('')
      queryClient.setQueryData(['auth-user'], user)
      await queryClient.invalidateQueries({ queryKey: ['auth-user'] })
      routeUser(user, redirectTo)
    },
    onError: (error) => {
      const apiError = error as ApiError
      setErrorMessage(apiError.message || 'Unable to sign in.')
    },
  })

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage('')
    loginMutation.mutate({ username: username.trim(), password, role })
  }

  return (
    <section className="auth-layout">
      <article className="auth-hero">
        <p className="eyebrow">Canonical Registry Access</p>
        <h2>Admin, doctor, and user sign-in</h2>
        <p className="hero-text">
          Use your Django account to access the registry. Each sign-in path now validates
          the selected role and redirects to the correct workflow after authentication.
        </p>
        <div className="auth-role-grid">
          <div className="auth-role-card">
            <span className="compare-summary-label">Admin</span>
            <strong>Registry oversight inside the React workspace, with optional Django admin access.</strong>
          </div>
          <div className="auth-role-card">
            <span className="compare-summary-label">Doctor</span>
            <strong>Doctor-specific clinical search, review, and patient observation workflow.</strong>
          </div>
          <div className="auth-role-card">
            <span className="compare-summary-label">User</span>
            <strong>General authenticated access to the registry workspace.</strong>
          </div>
        </div>
      </article>

      <article className="auth-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Sign In</p>
            <h3>Enter your account credentials</h3>
          </div>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="filter-field">
            <span>Sign in as</span>
            <div className="auth-role-selector">
              <button
                type="button"
                className={role === 'admin' ? 'auth-role-option auth-role-option-active' : 'auth-role-option'}
                onClick={() => setRole('admin')}
              >
                Admin
              </button>
              <button
                type="button"
                className={role === 'doctor' ? 'auth-role-option auth-role-option-active' : 'auth-role-option'}
                onClick={() => setRole('doctor')}
              >
                Doctor
              </button>
              <button
                type="button"
                className={role === 'user' ? 'auth-role-option auth-role-option-active' : 'auth-role-option'}
                onClick={() => setRole('user')}
              >
                User
              </button>
            </div>
          </label>
          <label className="filter-field">
            <span>Username</span>
            <input
              className="auth-input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              placeholder="Enter username"
            />
          </label>
          <label className="filter-field">
            <span>Password</span>
            <input
              className="auth-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              placeholder="Enter password"
            />
          </label>
          {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}
          <button
            className="primary-button auth-submit"
            type="submit"
            disabled={loginMutation.isPending || !username.trim() || !password}
          >
            {loginMutation.isPending ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </article>
    </section>
  )
}
