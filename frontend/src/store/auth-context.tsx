/* The provider, hook, and context live together so authentication state has one owner. */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import type { LoginInput, RegisterInput, UserProfile } from '../auth/types'
import { api, ensureCsrf, setUnauthorizedHandler } from '../services/api/client'

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

interface AuthContextValue {
  status: AuthStatus
  user: UserProfile | null
  login: (input: LoginInput) => Promise<void>
  register: (input: RegisterInput) => Promise<string>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<UserProfile | null>(null)

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null)
      setStatus('unauthenticated')
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function bootstrap() {
      try {
        await ensureCsrf()
        const result = await api.get<UserProfile>('/api/v1/auth/me')
        if (!cancelled) {
          setUser(result.data)
          setStatus('authenticated')
        }
      } catch {
        if (!cancelled) {
          setUser(null)
          setStatus('unauthenticated')
        }
      }
    }
    void bootstrap()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (input: LoginInput) => {
    const result = await api.post<UserProfile>('/api/v1/auth/login', input)
    setUser(result.data)
    setStatus('authenticated')
  }, [])

  const register = useCallback(async (input: RegisterInput) => {
    const result = await api.post<UserProfile>('/api/v1/auth/register', input)
    return result.message
  }, [])

  const logout = useCallback(async () => {
    await api.post<undefined>('/api/v1/auth/logout')
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  const value = useMemo(
    () => ({ status, user, login, register, logout }),
    [status, user, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return value
}

export { AuthContext }
