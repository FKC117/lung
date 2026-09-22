import { Suspense, lazy, useEffect, useState } from 'react'
import { Menu, Moon, Sun, X } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom'
import './App.css'
import './themes.css'
import { fetchCurrentUser, fetchSiteSettings, logoutUser, type ApiError, type AuthUser } from './api'
import { LoadingState } from './components/registry-ui'

const PatientSearchPage = lazy(() => import('./pages/PatientSearchPage'))
const PatientDetailPage = lazy(() => import('./pages/PatientDetailPage'))
const EntriesPatientEntryPage = lazy(() => import('./pages/EntriesPatientEntryPage'))
const EntriesPatientListPage = lazy(() => import('./pages/EntriesPatientListPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'))
const LongitudinalAnalyticsPage = lazy(() => import('./pages/LongitudinalAnalyticsPage'))
const PrescriptionReviewPage = lazy(() => import('./pages/PrescriptionReviewPage'))

function routeAuthenticatedUser(user: AuthUser, navigate: ReturnType<typeof useNavigate>) {
  if (user.default_redirect.startsWith('/admin')) {
    window.location.assign(user.default_redirect)
    return
  }
  navigate(user.default_redirect, { replace: true })
}

function LoginRedirect({ user }: { user: AuthUser }) {
  const navigate = useNavigate()

  useEffect(() => {
    routeAuthenticatedUser(user, navigate)
  }, [navigate, user])

  return (
    <section className="panel">
      <LoadingState label="Redirecting to your workspace" />
    </section>
  )
}

function AppHeader({
  fullName,
  role,
  onLogout,
  isLoggingOut,
  siteSettings,
  theme,
  onToggleTheme,
}: {
  fullName: string
  role: 'admin' | 'doctor' | 'user'
  onLogout: () => void
  isLoggingOut: boolean
  siteSettings: {
    site_title: string
    header_eyebrow: string
    site_description: string
    logo_url: string
    logo_alt_text: string
  }
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <header className="topbar">
      <div className="topbar-brand">
        {siteSettings.logo_url ? (
          <img className="topbar-logo" src={siteSettings.logo_url} alt={siteSettings.logo_alt_text} />
        ) : null}
        <div>
          <p className="eyebrow">{siteSettings.header_eyebrow}</p>
          <h1>{siteSettings.site_title}</h1>
          {siteSettings.site_description ? <p className="topbar-description">{siteSettings.site_description}</p> : null}
        </div>
      </div>
      <button
        type="button"
        className="mobile-menu-toggle"
        onClick={() => setMobileMenuOpen((open) => !open)}
        aria-expanded={mobileMenuOpen}
        aria-controls="mobile-primary-navigation"
        aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
      >
        {mobileMenuOpen ? <X size={21} /> : <Menu size={21} />}
      </button>
      <div className={`topbar-actions${mobileMenuOpen ? ' is-open' : ''}`}>
        <nav id="mobile-primary-navigation" className="topnav" aria-label="Primary">
          <NavLink
            to="/patients"
            className={({ isActive }) =>
              isActive ? 'topnav-link topnav-link-active' : 'topnav-link'
            }
            onClick={() => setMobileMenuOpen(false)}
          >
            Patients
          </NavLink>
          <NavLink
            to="/analytics"
            className={({ isActive }) =>
              isActive ? 'topnav-link topnav-link-active' : 'topnav-link'
            }
            onClick={() => setMobileMenuOpen(false)}
          >
            Summary dashboard
          </NavLink>
          <NavLink
            to="/longitudinal-analytics"
            className={({ isActive }) =>
              isActive ? 'topnav-link topnav-link-active' : 'topnav-link'
            }
            onClick={() => setMobileMenuOpen(false)}
          >
            Longitudinal Insights
          </NavLink>
          <NavLink
            to="/entries/new"
            className={({ isActive }) =>
              isActive ? 'topnav-link topnav-link-active' : 'topnav-link'
            }
            onClick={() => setMobileMenuOpen(false)}
          >
            New Entry
          </NavLink>
          <NavLink
            to="/prescriptions"
            className={({ isActive }) =>
              isActive ? 'topnav-link topnav-link-active' : 'topnav-link'
            }
            onClick={() => setMobileMenuOpen(false)}
          >
            Prescriptions
          </NavLink>
          {role === 'admin' ? (
            <a className="topnav-link" href="/admin/" onClick={() => setMobileMenuOpen(false)}>
              Django Admin
            </a>
          ) : null}
        </nav>
        <div className="user-badge-cluster">
          <span className="data-pill">
            {role === 'admin' ? 'Registry Admin' : role === 'doctor' ? 'Doctor' : 'User'}
          </span>
          <span className="data-pill">{fullName}</span>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setMobileMenuOpen(false)
              onLogout()
            }}
            disabled={isLoggingOut}
          >
            {isLoggingOut ? 'Signing out...' : 'Logout'}
          </button>
        </div>
      </div>
      <button
        type="button"
        className={theme === 'dark' ? 'theme-toggle theme-toggle-dark' : 'theme-toggle'}
        onClick={onToggleTheme}
        aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      >
        <Sun size={14} aria-hidden="true" />
        <span className="theme-toggle-thumb">{theme === 'dark' ? <Moon size={13} /> : null}</span>
        <Moon size={14} aria-hidden="true" />
      </button>
    </header>
  )
}

function ProtectedRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="/patients" replace />} />
      <Route path="patients/new" element={<EntriesPatientEntryPage />} />
      <Route path="entries/new" element={<EntriesPatientEntryPage />} />
      <Route path="entries/patients" element={<EntriesPatientListPage />} />
      <Route path="entries/patients/:patientId" element={<PatientDetailPage />} />
      <Route path="patients" element={<PatientSearchPage />} />
      <Route path="analytics" element={<AnalyticsPage />} />
      <Route path="longitudinal-analytics" element={<LongitudinalAnalyticsPage />} />
      <Route path="prescriptions" element={<PrescriptionReviewPage />} />
      <Route path="patients/:registryId" element={<PatientDetailPage />} />
      <Route path="*" element={<Navigate to="/patients" replace />} />
    </Routes>
  )
}

function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [theme, setTheme] = useState<'light' | 'dark'>(
    () => (window.localStorage.getItem('lung-registry-theme') === 'dark' ? 'dark' : 'light'),
  )

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('lung-registry-theme', theme)
  }, [theme])
  const authQuery = useQuery({
    queryKey: ['auth-user'],
    queryFn: fetchCurrentUser,
    retry: false,
  })
  const siteSettingsQuery = useQuery({
    queryKey: ['site-settings'],
    queryFn: fetchSiteSettings,
    staleTime: Infinity,
  })
  const siteSettings = siteSettingsQuery.data ?? {
    site_title: 'Lungcancer Registry',
    header_eyebrow: 'Lung Cancer Registry',
    site_description: '',
    logo_url: '',
    logo_alt_text: 'Lungcancer Registry logo',
    favicon_url: '',
  }

  useEffect(() => {
    document.title = siteSettings.site_title
    const favicon = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
    if (favicon && siteSettings.favicon_url) favicon.href = siteSettings.favicon_url
  }, [siteSettings.favicon_url, siteSettings.site_title])
  const logoutMutation = useMutation({
    mutationFn: logoutUser,
    onSuccess: async () => {
      queryClient.setQueryData(['auth-user'], null)
      await queryClient.cancelQueries({ queryKey: ['auth-user'] })
      queryClient.removeQueries({ queryKey: ['auth-user'] })
      navigate('/login', { replace: true })
    },
  })

  if (authQuery.isLoading) {
    return (
      <div className="app-shell">
        <main className="page-frame">
          <section className="panel">
            <LoadingState label="Checking session" />
          </section>
        </main>
      </div>
    )
  }

  const authError = authQuery.error as ApiError | null
  const isUnauthenticated = authError?.status === 401 || authError?.status === 403
  const user = isUnauthenticated ? null : authQuery.data ?? null
  const showHeader = Boolean(user) && location.pathname !== '/login'

  return (
    <div className="app-shell">
      {showHeader ? (
        <AppHeader
          fullName={user?.full_name || user?.username || 'User'}
          role={user?.role || 'user'}
          onLogout={() => logoutMutation.mutate()}
          isLoggingOut={logoutMutation.isPending}
          siteSettings={siteSettings}
          theme={theme}
          onToggleTheme={() => setTheme((current) => (current === 'light' ? 'dark' : 'light'))}
        />
      ) : null}
      <main className="page-frame">
        <Suspense
          fallback={
            <section className="panel">
              <LoadingState label="Loading route" />
            </section>
          }
        >
          <Routes>
            <Route
              path="/login"
              element={
                user ? (
                  <LoginRedirect user={user} />
                ) : (
                  <LoginPage />
                )
              }
            />
            <Route
              path="/*"
              element={
                isUnauthenticated || !user ? (
                  <Navigate
                    to="/login"
                    replace
                    state={{ from: { pathname: location.pathname } }}
                  />
                ) : (
                  <ProtectedRoutes />
                )
              }
            />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}

export default App
