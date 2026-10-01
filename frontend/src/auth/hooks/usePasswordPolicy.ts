import { useEffect, useState } from 'react'

import type { PasswordPolicy } from '../types'
import { api } from '../../services/api/client'

export function usePasswordPolicy() {
  const [policy, setPolicy] = useState<PasswordPolicy | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const result = await api.get<PasswordPolicy>('/api/v1/auth/password-policy')
        if (!cancelled) {
          setPolicy(result.data)
        }
      } catch {
        if (!cancelled) {
          setError(true)
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  return { policy, error }
}
