export interface FieldError {
  field: string
  code: string
  message: string
}

export interface ApiSuccess<T> {
  data: T
  message: string
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: FieldError[]

  constructor(message: string, status: number, code: string, details: FieldError[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

interface ErrorBody {
  error?: {
    code?: string
    message?: string
    details?: FieldError[]
  }
}

export async function toApiError(response: Response): Promise<ApiError> {
  let payload: ErrorBody | null = null
  try {
    payload = (await response.json()) as ErrorBody
  } catch {
    payload = null
  }
  return new ApiError(
    payload?.error?.message ?? 'The request could not be completed.',
    response.status,
    payload?.error?.code ?? 'REQUEST_FAILED',
    payload?.error?.details ?? [],
  )
}
