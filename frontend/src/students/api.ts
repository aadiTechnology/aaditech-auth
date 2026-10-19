import { api } from '../services/api/client'
import type { StudentDetail, StudentListData, StudentSummary } from './types'

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

export function listStudents(params: Record<string, string | number | undefined>) {
  return api.get<StudentListData>(`/api/v1/students${queryString(params)}`)
}

export function getStudentSummary() {
  return api.get<StudentSummary>('/api/v1/students/summary')
}

export function getStudent(studentId: string) {
  return api.get<StudentDetail>(`/api/v1/students/${studentId}`)
}

export function createStudent(body: unknown) {
  return api.post<StudentDetail>('/api/v1/students', body)
}

export function updateStudent(studentId: string, body: unknown) {
  return api.patch<StudentDetail>(`/api/v1/students/${studentId}`, body)
}

export function archiveStudent(studentId: string) {
  return api.post<StudentDetail>(`/api/v1/students/${studentId}/archive`)
}

export function linkParent(studentId: string, body: { parent_id: string; relationship: string | null }) {
  return api.post<StudentDetail>(`/api/v1/students/${studentId}/parents`, body)
}

export function unlinkParent(studentId: string, parentId: string) {
  return api.delete<StudentDetail>(`/api/v1/students/${studentId}/parents/${parentId}`)
}
