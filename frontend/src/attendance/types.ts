export type AttendanceStatus = 'present' | 'absent' | 'late' | 'excused'
export type Completion = 'not_recorded' | 'partial' | 'complete' | 'no_students'

export interface RosterMark {
  id: string
  status: AttendanceStatus
  notes: string | null
  version: number
  updated_at: string
}

export interface RosterStudent {
  student_id: string
  student_code: string
  full_name: string
  student_status: string
  attendance: RosterMark | null
}

export interface ClassRoster {
  id: string
  batch_id: string
  batch_name: string
  batch_code: string
  class_date: string
  start_time: string
  end_time: string
  topic: string | null
  class_status: string
  completion: Completion
  enrolled_count: number
  recorded_count: number
  students: RosterStudent[]
}

export interface AttendanceClassItem {
  id: string
  batch_id: string
  batch_name: string
  batch_code: string
  class_date: string
  start_time: string
  end_time: string
  topic: string | null
  class_status: string
  completion: Completion
  enrolled_count: number
  recorded_count: number
}

export interface HistoryItem {
  id: string
  scheduled_class_id: string
  student_id: string
  student_code: string
  full_name: string
  batch_id: string
  batch_name: string
  batch_code: string
  class_date: string
  start_time: string
  end_time: string
  topic: string | null
  class_status: string
  status: AttendanceStatus
  notes: string | null
  version: number
  updated_at: string
}

export interface SummaryItem {
  student_id: string
  student_code: string
  full_name: string
  present: number
  absent: number
  late: number
  excused: number
  recorded: number
  eligible: number
  percentage: number | null
}
