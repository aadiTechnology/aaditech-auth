import { api } from '../services/api/client'
import type { ParentDetail, ParentListData } from './types'

function queryString(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export function listParents(params: Record<string, string | number | undefined>) {
  return api.get<ParentListData>(`/api/v1/parents${queryString(params)}`)
}

export function getParent(parentId: string) {
  return api.get<ParentDetail>(`/api/v1/parents/${parentId}`)
}

export function createParent(body: unknown) {
  return api.post<ParentDetail>('/api/v1/parents', body)
}

export function updateParent(parentId: string, body: unknown) {
  return api.patch<ParentDetail>(`/api/v1/parents/${parentId}`, body)
}

export function archiveParent(parentId: string) {
  return api.post<ParentDetail>(`/api/v1/parents/${parentId}/archive`)
}

export function linkStudent(parentId: string, body: { student_id: string; relationship: string | null }) {
  return api.post<ParentDetail>(`/api/v1/parents/${parentId}/students`, body)
}

export function unlinkStudent(parentId: string, studentId: string) {
  return api.delete<ParentDetail>(`/api/v1/parents/${parentId}/students/${studentId}`)
}
