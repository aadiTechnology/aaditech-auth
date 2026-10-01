import { Navigate, Route, Routes } from 'react-router-dom'

import { GuestRoute, PermissionRoute, ProtectedRoute } from '../../access/components/RouteGuards'
import { AccessDeniedPage } from '../../access/pages/AccessDeniedPage'
import { AccessManagementPage } from '../../access/pages/AccessManagementPage'
import { HomePage } from '../../access/pages/HomePage'
import { ForgotPasswordPage } from '../../auth/pages/ForgotPasswordPage'
import { LoginPage } from '../../auth/pages/LoginPage'
import { RegisterPage } from '../../auth/pages/RegisterPage'
import { ResetPasswordPage } from '../../auth/pages/ResetPasswordPage'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { NotFoundPage } from '../../components/common/NotFoundPage'
import { AppLayout } from '../../layouts/AppLayout/AppLayout'
import { AuthLayout } from '../../layouts/AuthLayout/AuthLayout'
import { useAuth } from '../../store/auth-context'

function RootRedirect() {
  const { status } = useAuth()
  if (status === 'loading') {
    return <LoadingScreen />
  }
  return <Navigate to={status === 'authenticated' ? '/app' : '/login'} replace />
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
        <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />
        <Route path="/forgot-password" element={<GuestRoute><ForgotPasswordPage /></GuestRoute>} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>
      <Route path="/app" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<HomePage />} />
        <Route path="access-denied" element={<AccessDeniedPage />} />
        <Route
          path="admin/access"
          element={
            <PermissionRoute permission="users.read">
              <AccessManagementPage />
            </PermissionRoute>
          }
        />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
