import { api } from '../services/api/client'
import type { ClassListData, ScheduledClassDetail } from '../timetable/types'

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

export function listUpcomingMeetings(params: Record<string, string | number | boolean | undefined>) {
  return api.get<ClassListData>(`/api/v1/meet/upcoming${queryString(params)}`)
}

export function getMeeting(classId: string) {
  return api.get<ScheduledClassDetail>(`/api/v1/meet/classes/${classId}`)
}

export function updateMeeting(classId: string, body: { version: number; meet_url: string | null }) {
  return api.patch<ScheduledClassDetail>(`/api/v1/meet/classes/${classId}`, body)
}
