import { ApiError } from '../services/api/errors'
import { api } from '../services/api/client'

export type SummaryMetricId = 'students' | 'batches' | 'todayClasses' | 'pendingFees'

export type SummaryMetricStatus = 'loading' | 'ready' | 'empty' | 'unavailable' | 'error'

export interface SummaryMetric {
  id: SummaryMetricId
  status: SummaryMetricStatus
  value: number | null
  href?: string
}

export interface UpcomingClass {
  id: string
  batch_id: string
  batch_name: string
  batch_code: string
  class_date: string
  start_time: string
  end_time: string
  topic: string | null
  meet_url?: string | null
  meet_status?: 'added' | 'missing'
}

export type UpcomingStatus = 'ready' | 'empty' | 'unavailable' | 'error'

export interface TodayAttendanceClass {
  id: string
  batch_id: string
  batch_name: string
  class_date: string
  start_time: string
  end_time: string
  topic: string | null
  completion: 'not_recorded' | 'partial' | 'complete' | 'no_students'
  enrolled_count: number
  recorded_count: number
}

export interface DashboardData {
  metrics: SummaryMetric[]
  upcoming: UpcomingClass[]
  upcomingStatus: UpcomingStatus
  todayClasses: UpcomingClass[]
  todayStatus: UpcomingStatus
  attendanceToday: TodayAttendanceClass[]
  attendanceTodayStatus: UpcomingStatus
}

interface CountBody {
  active_count: number
}

interface TimetableSummaryBody {
  today_count: number
  today?: UpcomingClass[]
  upcoming: UpcomingClass[]
}

interface AttendanceTodayBody {
  classes: TodayAttendanceClass[]
}

const pendingFees: SummaryMetric = { id: 'pendingFees', status: 'unavailable', value: null }

function denied(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403)
}

function countMetric(
  id: SummaryMetricId,
  href: string,
  result: PromiseSettledResult<{ data: CountBody }>,
  pick: (data: CountBody) => number,
): SummaryMetric {
  if (result.status === 'fulfilled') {
    return { id, status: 'ready', value: pick(result.value.data), href }
  }
  if (denied(result.reason)) {
    return { id, status: 'unavailable', value: null, href }
  }
  return { id, status: 'error', value: null, href }
}

/**
 * Student, batch, and today's class counts come from the API.
 * Meeting links and attendance completion come from the same live responses.
 * Pending fees stay unavailable until that module exists.
 * A forbidden or failed count is not replaced with a made-up number.
 */
export async function loadDashboardMetrics(): Promise<DashboardData> {
  const [students, batches, timetable, attendance] = await Promise.allSettled([
    api.get<CountBody>('/api/v1/students/summary'),
    api.get<CountBody>('/api/v1/batches/summary'),
    api.get<TimetableSummaryBody>('/api/v1/timetable/summary'),
    api.get<AttendanceTodayBody>('/api/v1/attendance/today'),
  ])

  let today: SummaryMetric
  let upcoming: UpcomingClass[] = []
  let upcomingStatus: UpcomingStatus
  let todayClasses: UpcomingClass[] = []
  let todayStatus: UpcomingStatus
  if (timetable.status === 'fulfilled') {
    today = {
      id: 'todayClasses',
      status: 'ready',
      value: timetable.value.data.today_count,
      href: '/app/timetable',
    }
    upcoming = timetable.value.data.upcoming
    upcomingStatus = upcoming.length === 0 ? 'empty' : 'ready'
    todayClasses = timetable.value.data.today ?? []
    todayStatus = todayClasses.length === 0 ? 'empty' : 'ready'
  } else if (denied(timetable.reason)) {
    today = { id: 'todayClasses', status: 'unavailable', value: null, href: '/app/timetable' }
    upcomingStatus = 'unavailable'
    todayStatus = 'unavailable'
  } else {
    today = { id: 'todayClasses', status: 'error', value: null, href: '/app/timetable' }
    upcomingStatus = 'error'
    todayStatus = 'error'
  }

  let attendanceToday: TodayAttendanceClass[] = []
  let attendanceTodayStatus: UpcomingStatus
  if (attendance.status === 'fulfilled' && Array.isArray(attendance.value.data.classes)) {
    attendanceToday = attendance.value.data.classes
    attendanceTodayStatus = attendanceToday.length === 0 ? 'empty' : 'ready'
  } else if (attendance.status === 'rejected' && denied(attendance.reason)) {
    attendanceTodayStatus = 'unavailable'
  } else {
    attendanceTodayStatus = 'error'
  }

  return {
    metrics: [
      countMetric('students', '/app/students', students, (data) => data.active_count),
      countMetric('batches', '/app/batches', batches, (data) => data.active_count),
      today,
      pendingFees,
    ],
    upcoming,
    upcomingStatus,
    todayClasses,
    todayStatus,
    attendanceToday,
    attendanceTodayStatus,
  }
}
