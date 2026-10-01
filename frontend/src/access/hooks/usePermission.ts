import { useAuth } from '../../store/auth-context'

export function usePermission() {
  const { user } = useAuth()
  const hasPermission = (permission: string) => user?.permissions.includes(permission) ?? false
  const hasRole = (role: string) => user?.roles.includes(role) ?? false
  return { hasPermission, hasRole }
}
