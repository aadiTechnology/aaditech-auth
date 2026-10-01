import { ApiError, toApiError, type ApiSuccess } from './errors'

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

let csrfToken: string | null = null
let refreshPromise: Promise<boolean> | null = null
let unauthorizedHandler: (() => void) | null = null

const refreshSkipped = new Set([
  '/api/v1/auth/login',
  '/api/v1/auth/refresh',
  '/api/v1/auth/register',
  '/api/v1/auth/forgot-password',
  '/api/v1/auth/reset-password',
  '/api/v1/auth/csrf',
])

export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler
}

export async function ensureCsrf(): Promise<void> {
  if (csrfToken) {
    return
  }
  const response = await fetch(`${baseUrl}/api/v1/auth/csrf`, {
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    throw await toApiError(response)
  }
  const body = (await response.json()) as ApiSuccess<{ csrf_token: string }>
  csrfToken = body.data.csrf_token
}

async function refreshSession(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        if (!csrfToken) {
          await ensureCsrf()
        }
        const headers: Record<string, string> = { Accept: 'application/json' }
        if (csrfToken) {
          headers['X-CSRF-Token'] = csrfToken
        }
        const response = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers,
        })
        return response.ok
      } catch {
        return false
      }
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  allowRetry = true,
): Promise<ApiSuccess<T>> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (method !== 'GET' && method !== 'HEAD') {
    if (!csrfToken) {
      await ensureCsrf()
    }
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken
    }
  }

  let response: Response
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      credentials: 'include',
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Network error. Check your connection and try again.', 0, 'NETWORK_ERROR')
  }

  if (response.status === 403 && allowRetry) {
    const error = await toApiError(response)
    if (error.code === 'CSRF_VALIDATION_FAILED') {
      csrfToken = null
      await ensureCsrf()
      return request(method, path, body, false)
    }
    throw error
  }

  if (response.status === 401 && allowRetry && !refreshSkipped.has(path)) {
    const refreshed = await refreshSession()
    if (refreshed) {
      return request(method, path, body, false)
    }
    unauthorizedHandler?.()
  }

  if (!response.ok) {
    throw await toApiError(response)
  }
  if (response.status === 204) {
    return { data: undefined as T, message: '' }
  }
  return (await response.json()) as ApiSuccess<T>
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
}
