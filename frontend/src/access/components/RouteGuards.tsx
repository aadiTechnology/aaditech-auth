import { Navigate } from 'react-router-dom'

import { LoadingScreen } from '../../components/common/LoadingScreen'
import { useAuth } from '../../store/auth-context'
import type { ReactNode } from 'react'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  if (status === 'loading') {
    return <LoadingScreen />
  }
  if (status !== 'authenticated') {
    return <Navigate to="/login" replace />
  }
  return children
}

export function GuestRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  if (status === 'loading') {
    return <LoadingScreen />
  }
  if (status === 'authenticated') {
    return <Navigate to="/app" replace />
  }
  return children
}

export function PermissionRoute({
  permission,
  children,
}: {
  permission: string
  children: ReactNode
}) {
  const { status, user } = useAuth()
  if (status === 'loading') {
    return <LoadingScreen />
  }
  if (status !== 'authenticated') {
    return <Navigate to="/login" replace />
  }
  if (!user?.permissions.includes(permission)) {
    return <Navigate to="/app/access-denied" replace />
  }
  return children
}
