export interface LinkedStudent {
  id: string
  student_code: string
  full_name: string
  grade: string | null
  relationship: string | null
  status: string
}

export interface ParentListItem {
  id: string
  full_name: string
  phone: string | null
  email: string | null
  status: string
  students: LinkedStudent[]
}

export interface ParentDetail {
  id: string
  full_name: string
  phone: string | null
  email: string | null
  address: string | null
  notes: string | null
  status: string
  version: number
  archived_at: string | null
  students: LinkedStudent[]
}

export interface ParentListData {
  items: ParentListItem[]
  total: number
  limit: number
  offset: number
}

export interface ParentFormValues {
  full_name: string
  phone: string
  email: string
  address: string
  notes: string
  status: 'active' | 'archived'
}

export const emptyParentForm: ParentFormValues = {
  full_name: '',
  phone: '',
  email: '',
  address: '',
  notes: '',
  status: 'active',
}
