export interface ParentName {
  id: string
  full_name: string
  relationship: string | null
}

export interface ParentContact extends ParentName {
  phone: string | null
  email: string | null
  status: string
}

export interface StudentListItem {
  id: string
  student_code: string
  full_name: string
  grade: string | null
  school_name: string | null
  status: string
  enrollment_date: string | null
  parents: ParentName[]
}

export interface StudentDetail {
  id: string
  student_code: string
  full_name: string
  date_of_birth: string | null
  school_name: string | null
  grade: string | null
  address: string | null
  enrollment_date: string | null
  status: string
  notes: string | null
  version: number
  archived_at: string | null
  parents: ParentContact[]
}

export interface StudentListData {
  items: StudentListItem[]
  total: number
  limit: number
  offset: number
}

export interface StudentSummary {
  active_count: number
}

export type StudentStatus = 'active' | 'inactive' | 'archived'
export type ParentLinkMode = 'none' | 'existing' | 'new'

export interface StudentFormValues {
  full_name: string
  status: StudentStatus
  date_of_birth: string
  school_name: string
  grade: string
  address: string
  enrollment_date: string
  notes: string
  parentMode: ParentLinkMode
  parent_id: string
  relationship: string
  parent_full_name: string
  parent_phone: string
  parent_email: string
}

export const emptyStudentForm: StudentFormValues = {
  full_name: '',
  status: 'active',
  date_of_birth: '',
  school_name: '',
  grade: '',
  address: '',
  enrollment_date: '',
  notes: '',
  parentMode: 'none',
  parent_id: '',
  relationship: '',
  parent_full_name: '',
  parent_phone: '',
  parent_email: '',
}

export const GRADES = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const
