import { api } from '../services/api/client'
import type { AttendanceClassItem, ClassRoster, HistoryItem, SummaryItem } from './types'

function queryString(params: Record<string, string | number | boolean | undefined>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export function listAttendanceClasses(params: Record<string, string | number | boolean | undefined>) {
  return api.get<{ items: AttendanceClassItem[]; total: number }>(`/api/v1/attendance/classes${queryString(params)}`)
}

export function getRoster(classId: string) {
  return api.get<ClassRoster>(`/api/v1/attendance/classes/${classId}`)
}

export function saveAttendance(
  classId: string,
  marks: Array<{ student_id: string; status: string; notes?: string | null; version?: number | null }>,
) {
  return api.post<ClassRoster>(`/api/v1/attendance/classes/${classId}`, { marks })
}

export function listHistory(params: Record<string, string | number | boolean | undefined>) {
  return api.get<{ items: HistoryItem[]; total: number }>(`/api/v1/attendance/history${queryString(params)}`)
}

export function listSummary(params: Record<string, string | number | boolean | undefined>) {
  return api.get<{ items: SummaryItem[] }>(`/api/v1/attendance/summary${queryString(params)}`)
}
