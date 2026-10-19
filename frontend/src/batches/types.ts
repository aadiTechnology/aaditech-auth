export interface NextClass {
  id: string
  class_date: string
  start_time: string
  end_time: string
}

export interface BatchStudentItem {
  id: string
  student_code: string
  full_name: string
  grade: string | null
  status: string
}

export interface BatchListItem {
  id: string
  batch_code: string
  name: string
  subject: string | null
  grade: string | null
  status: string
  student_count: number
  next_class: NextClass | null
}

export interface BatchDetail extends BatchListItem {
  description: string | null
  version: number
  archived_at: string | null
  students: BatchStudentItem[]
}

export interface BatchListData {
  items: BatchListItem[]
  total: number
  limit: number
  offset: number
}

export interface BatchSummary {
  active_count: number
}

export interface BatchFormValues {
  name: string
  subject: string
  grade: string
  description: string
  status: 'active' | 'inactive'
}

export const emptyBatchForm: BatchFormValues = {
  name: '',
  subject: '',
  grade: '',
  description: '',
  status: 'active',
}

export interface SelectedStudent {
  id: string
  student_code: string
  full_name: string
}
