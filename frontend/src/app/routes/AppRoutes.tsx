import { Navigate, Route, Routes } from 'react-router-dom'

import { GuestRoute, PermissionRoute, ProtectedRoute } from '../../access/components/RouteGuards'
import { AccessDeniedPage } from '../../access/pages/AccessDeniedPage'
import { AccessManagementPage } from '../../access/pages/AccessManagementPage'
import { DashboardPage } from '../../dashboard/pages/DashboardPage'
import { ForgotPasswordPage } from '../../auth/pages/ForgotPasswordPage'
import { LoginPage } from '../../auth/pages/LoginPage'
import { RegisterPage } from '../../auth/pages/RegisterPage'
import { ResetPasswordPage } from '../../auth/pages/ResetPasswordPage'
import { LoadingScreen } from '../../components/common/LoadingScreen'
import { NotFoundPage } from '../../components/common/NotFoundPage'
import { AppLayout } from '../../layouts/AppLayout/AppLayout'
import { AuthLayout } from '../../layouts/AuthLayout/AuthLayout'
import { BatchDetailPage } from '../../batches/pages/BatchDetailPage'
import { BatchFormPage } from '../../batches/pages/BatchFormPage'
import { BatchListPage } from '../../batches/pages/BatchListPage'
import { ParentDetailPage } from '../../parents/pages/ParentDetailPage'
import { ParentFormPage } from '../../parents/pages/ParentFormPage'
import { ParentListPage } from '../../parents/pages/ParentListPage'
import { StudentDetailPage } from '../../students/pages/StudentDetailPage'
import { TimetablePage } from '../../timetable/pages/TimetablePage'
import { StudentFormPage } from '../../students/pages/StudentFormPage'
import { StudentListPage } from '../../students/pages/StudentListPage'
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
        <Route index element={<DashboardPage />} />
        <Route path="access-denied" element={<AccessDeniedPage />} />
        <Route
          path="students"
          element={
            <PermissionRoute permission="students.read">
              <StudentListPage />
            </PermissionRoute>
          }
        />
        <Route
          path="students/new"
          element={
            <PermissionRoute permission="students.create">
              <StudentFormPage />
            </PermissionRoute>
          }
        />
        <Route
          path="students/:studentId"
          element={
            <PermissionRoute permission="students.read">
              <StudentDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="students/:studentId/edit"
          element={
            <PermissionRoute permission="students.update">
              <StudentFormPage />
            </PermissionRoute>
          }
        />
        <Route
          path="parents"
          element={
            <PermissionRoute permission="parents.read">
              <ParentListPage />
            </PermissionRoute>
          }
        />
        <Route
          path="parents/new"
          element={
            <PermissionRoute permission="parents.create">
              <ParentFormPage />
            </PermissionRoute>
          }
        />
        <Route
          path="parents/:parentId"
          element={
            <PermissionRoute permission="parents.read">
              <ParentDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="parents/:parentId/edit"
          element={
            <PermissionRoute permission="parents.update">
              <ParentFormPage />
            </PermissionRoute>
          }
        />
        <Route
          path="batches"
          element={
            <PermissionRoute permission="batches.read">
              <BatchListPage />
            </PermissionRoute>
          }
        />
        <Route
          path="batches/new"
          element={
            <PermissionRoute permission="batches.create">
              <BatchFormPage />
            </PermissionRoute>
          }
        />
        <Route
          path="batches/:batchId"
          element={
            <PermissionRoute permission="batches.read">
              <BatchDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="batches/:batchId/edit"
          element={
            <PermissionRoute permission="batches.update">
              <BatchFormPage />
            </PermissionRoute>
          }
        />
        <Route
          path="timetable"
          element={
            <PermissionRoute permission="timetable.read">
              <TimetablePage />
            </PermissionRoute>
          }
        />
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
