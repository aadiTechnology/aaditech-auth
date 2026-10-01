export interface UserProfile {
  id: string
  full_name: string
  email: string
  preferred_language: string
  is_active: boolean
  email_verified: boolean
  roles: string[]
  permissions: string[]
}

export interface PasswordPolicy {
  min_length: number
  require_uppercase: boolean
  require_lowercase: boolean
  require_number: boolean
  require_special: boolean
  special_pattern: string
}

export interface LoginInput {
  email: string
  password: string
  remember_me: boolean
}

export interface RegisterInput {
  full_name: string
  email: string
  password: string
  confirm_password: string
  preferred_language: string
}

export interface AccessUser {
  id: string
  full_name: string
  email: string
  roles: string[]
  is_active: boolean
}

export interface UserListData {
  items: AccessUser[]
  total: number
}

export interface PermissionPublic {
  id: string
  key: string
  description: string
}

export interface RolePublic {
  id: string
  name: string
  description: string
  permissions: PermissionPublic[]
}
