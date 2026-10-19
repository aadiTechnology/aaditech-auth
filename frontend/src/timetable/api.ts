import { api } from '../services/api/client'
import type { ClassListData, PreviewData, ScheduledClassDetail, TimetableSummary } from './types'

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

export function getTimetableSummary() {
  return api.get<TimetableSummary>('/api/v1/timetable/summary')
}

export function listClasses(params: Record<string, string | number | boolean | undefined>) {
  return api.get<ClassListData>(`/api/v1/timetable${queryString(params)}`)
}

export function getClass(classId: string) {
  return api.get<ScheduledClassDetail>(`/api/v1/timetable/${classId}`)
}

export function createClass(body: unknown) {
  return api.post<ScheduledClassDetail>('/api/v1/timetable', body)
}

export function updateClass(classId: string, body: unknown) {
  return api.patch<ScheduledClassDetail>(`/api/v1/timetable/${classId}`, body)
}

export function cancelClass(classId: string) {
  return api.post<ScheduledClassDetail>(`/api/v1/timetable/${classId}/cancel`)
}

export function previewRecurring(body: unknown) {
  return api.post<PreviewData>('/api/v1/timetable/preview', body)
}

export function createRecurring(body: unknown) {
  return api.post<ClassListData>('/api/v1/timetable/recurring', body)
}
