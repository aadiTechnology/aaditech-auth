export interface ScheduledClassItem {
  id: string
  batch_id: string
  batch_name: string
  batch_code: string
  class_date: string
  start_time: string
  end_time: string
  topic: string | null
  status: string
  meet_url: string | null
  meet_status: 'added' | 'missing'
}

export interface ScheduledClassDetail extends ScheduledClassItem {
  notes: string | null
  version: number
  cancelled_at: string | null
}

export interface ClassListData {
  items: ScheduledClassItem[]
  total: number
}

export interface OccurrencePreview {
  class_date: string
  start_time: string
  end_time: string
  conflict: boolean
}

export interface PreviewData {
  occurrences: OccurrencePreview[]
  conflict_count: number
}

export interface TimetableSummary {
  today_count: number
  today?: Array<{
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
  }>
  upcoming: Array<{
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
  }>
}

export interface ClassFormValues {
  batch_id: string
  class_date: string
  start_time: string
  end_time: string
  topic: string
  notes: string
  repeat: boolean
  weekdays: number[]
  end_date: string
}

export const emptyClassForm: ClassFormValues = {
  batch_id: '',
  class_date: '',
  start_time: '',
  end_time: '',
  topic: '',
  notes: '',
  repeat: false,
  weekdays: [],
  end_date: '',
}
