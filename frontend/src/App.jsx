import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { Loading } from './components/ui'
import BeneficiaryLayout from './layouts/BeneficiaryLayout'
import InstitutionLayout from './layouts/InstitutionLayout'
import Login, { homeFor } from './pages/public/Login'
import { About, ForgotPassword, ResetPassword } from './pages/public/PasswordPages'

const Overview = lazy(() => import('./pages/app/Overview'))
const CaseDetail = lazy(() => import('./pages/app/CaseDetail'))
const Cases = lazy(() => import('./pages/app/Cases').then((m) => ({ default: m.CaseList })))
const CaseNew = lazy(() => import('./pages/app/Cases').then((m) => ({ default: m.CaseNew })))
const ReferralList = lazy(() => import('./pages/app/Referrals').then((m) => ({ default: m.ReferralList })))
const ReferralDetail = lazy(() => import('./pages/app/Referrals').then((m) => ({ default: m.ReferralDetail })))
const Appointments = lazy(() => import('./pages/app/Work').then((m) => ({ default: m.Appointments })))
const FollowUps = lazy(() => import('./pages/app/Work').then((m) => ({ default: m.FollowUps })))
const Reviews = lazy(() => import('./pages/app/Work').then((m) => ({ default: m.Reviews })))
const Assistance = lazy(() => import('./pages/app/Work').then((m) => ({ default: m.AssistanceRequests })))
const Notifications = lazy(() => import('./pages/app/Work').then((m) => ({ default: m.Notifications })))
const Settings = lazy(() => import('./pages/app/Settings'))
const Analytics = lazy(() => import('./pages/app/Analytics'))
const AnonymousReports = lazy(() => import('./pages/app/Communications').then((m) => ({ default: m.AnonymousReports })))
const AnonymousReportDetail = lazy(() => import('./pages/app/Communications').then((m) => ({ default: m.AnonymousReportDetail })))
const UssdSimulator = lazy(() => import('./pages/app/Communications').then((m) => ({ default: m.UssdSimulator })))
const SmsDashboard = lazy(() => import('./pages/app/Communications').then((m) => ({ default: m.SmsDashboard })))
const Users = lazy(() => import('./pages/admin/Admin').then((m) => ({ default: m.Users })))
const Institutions = lazy(() => import('./pages/admin/Admin').then((m) => ({ default: m.Institutions })))
const Services = lazy(() => import('./pages/admin/Admin').then((m) => ({ default: m.Services })))
const AuditLogs = lazy(() => import('./pages/admin/Admin').then((m) => ({ default: m.AuditLogs })))
const BenHome = lazy(() => import('./pages/me/Beneficiary').then((m) => ({ default: m.BeneficiaryHome })))
const BenCase = lazy(() => import('./pages/me/Beneficiary').then((m) => ({ default: m.BeneficiaryCase })))
const BenHelp = lazy(() => import('./pages/me/Beneficiary').then((m) => ({ default: m.RequestHelp })))
const BenSupport = lazy(() => import('./pages/me/Beneficiary').then((m) => ({ default: m.SupportServices })))
const BenSettings = lazy(() => import('./pages/me/Beneficiary').then((m) => ({ default: m.BeneficiarySettings })))

/** Route guards are for usability only — every API endpoint enforces authorisation itself. */
function RequireAuth({ portal, check, children }) {
  const { user, status } = useAuth()
  const location = useLocation()
  if (status === 'checking') return <div className="flex min-h-screen items-center justify-center"><Loading /></div>
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  const isBen = Boolean(user.permissions?.beneficiary_portal)
  if ((portal === 'beneficiary') !== isBen) return <Navigate to={homeFor(user)} replace />
  if (check && !check(user)) return <Navigate to={homeFor(user)} replace />
  return children
}

const can = (perm) => (u) => Boolean(u.permissions?.[perm])
const notAdmin = (u) => u.role !== 'ADMIN'

function PublicOnly({ children }) {
  const { user, status } = useAuth()
  if (status === 'checking') return <div className="flex min-h-screen items-center justify-center"><Loading /></div>
  return user ? <Navigate to={homeFor(user)} replace /> : children
}

export default function App() {
  const g = (el, check) => <RequireAuth portal="staff" check={check}>{el}</RequireAuth>
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/about" element={<About />} />

        <Route path="/app" element={<RequireAuth portal="staff"><InstitutionLayout /></RequireAuth>}>
          <Route index element={<Overview />} />
          <Route path="cases" element={g(<Cases />, notAdmin)} />
          <Route path="cases/new" element={g(<CaseNew />, can('register_case'))} />
          <Route path="cases/:id" element={g(<CaseDetail />, notAdmin)} />
          <Route path="referrals" element={g(<ReferralList />, notAdmin)} />
          <Route path="referrals/:id" element={g(<ReferralDetail />, notAdmin)} />
          <Route path="appointments" element={g(<Appointments />, notAdmin)} />
          <Route path="follow-ups" element={g(<FollowUps />, notAdmin)} />
          <Route path="reviews" element={g(<Reviews />, notAdmin)} />
          <Route path="assistance" element={g(<Assistance />, notAdmin)} />
          <Route path="anonymous-reports" element={g(<AnonymousReports />, can('triage_anonymous_reports'))} />
          <Route path="anonymous-reports/:id" element={g(<AnonymousReportDetail />, can('triage_anonymous_reports'))} />
          <Route path="analytics" element={g(<Analytics />, can('view_analytics'))} />
          <Route path="sms" element={g(<SmsDashboard />, can('view_analytics'))} />
          <Route path="ussd-simulator" element={<UssdSimulator />} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="settings" element={<Settings />} />
          <Route path="admin/users" element={g(<Users />, can('manage_users'))} />
          <Route path="admin/institutions" element={g(<Institutions />, can('manage_users'))} />
          <Route path="admin/services" element={g(<Services />, can('manage_users'))} />
          <Route path="admin/audit" element={g(<AuditLogs />, can('view_audit'))} />
        </Route>

        <Route path="/me" element={<RequireAuth portal="beneficiary"><BeneficiaryLayout /></RequireAuth>}>
          <Route index element={<BenHome />} />
          <Route path="cases/:id" element={<BenCase />} />
          <Route path="help" element={<BenHelp />} />
          <Route path="requests" element={<BenHelp />} />
          <Route path="support" element={<BenSupport />} />
          <Route path="messages" element={<Notifications beneficiary />} />
          <Route path="settings" element={<BenSettings />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  )
}
