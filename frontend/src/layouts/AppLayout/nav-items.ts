import AdminPanelSettingsOutlinedIcon from '@mui/icons-material/AdminPanelSettingsOutlined'
import CalendarMonthOutlinedIcon from '@mui/icons-material/CalendarMonthOutlined'
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined'
import FactCheckOutlinedIcon from '@mui/icons-material/FactCheckOutlined'
import GroupsOutlinedIcon from '@mui/icons-material/GroupsOutlined'
import PaymentsOutlinedIcon from '@mui/icons-material/PaymentsOutlined'
import PeopleOutlineIcon from '@mui/icons-material/PeopleOutline'
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined'
import SupervisorAccountOutlinedIcon from '@mui/icons-material/SupervisorAccountOutlined'
import VideoCallOutlinedIcon from '@mui/icons-material/VideoCallOutlined'
import type { ElementType } from 'react'

export interface AppNavItem {
  id: string
  labelKey: string
  icon: ElementType
  to?: string
  comingSoon?: boolean
  permission?: string
}

export const primaryNavItems: AppNavItem[] = [
  { id: 'dashboard', labelKey: 'dashboard', icon: DashboardOutlinedIcon, to: '/app' },
  { id: 'students', labelKey: 'students', icon: PeopleOutlineIcon, to: '/app/students', permission: 'students.read' },
  { id: 'parents', labelKey: 'parents', icon: SupervisorAccountOutlinedIcon, to: '/app/parents', permission: 'parents.read' },
  { id: 'batches', labelKey: 'batches', icon: GroupsOutlinedIcon, to: '/app/batches', permission: 'batches.read' },
  { id: 'timetable', labelKey: 'timetable', icon: CalendarMonthOutlinedIcon, to: '/app/timetable', permission: 'timetable.read' },
  { id: 'googleMeet', labelKey: 'googleMeet', icon: VideoCallOutlinedIcon, to: '/app/meet', permission: 'meet.read' },
  { id: 'attendance', labelKey: 'attendance', icon: FactCheckOutlinedIcon, to: '/app/attendance', permission: 'attendance.read' },
  { id: 'fees', labelKey: 'fees', icon: PaymentsOutlinedIcon, comingSoon: true },
  { id: 'receipts', labelKey: 'receipts', icon: ReceiptLongOutlinedIcon, comingSoon: true },
]

export const adminNavItems: AppNavItem[] = [
  {
    id: 'access',
    labelKey: 'accessManagement',
    icon: AdminPanelSettingsOutlinedIcon,
    to: '/app/admin/access',
    permission: 'users.read',
  },
]

export function isNavItemSelected(pathname: string, item: AppNavItem) {
  if (!item.to) {
    return false
  }
  if (item.to === '/app') {
    return pathname === '/app' || pathname === '/app/'
  }
  return pathname === item.to || pathname.startsWith(`${item.to}/`)
}

export function pageTitleKey(pathname: string) {
  if (pathname.startsWith('/app/admin/access')) {
    return 'accessManagement'
  }
  if (pathname.startsWith('/app/access-denied')) {
    return 'accessDenied'
  }
  if (pathname.startsWith('/app/students')) {
    return 'students'
  }
  if (pathname.startsWith('/app/parents')) {
    return 'parents'
  }
  if (pathname.startsWith('/app/batches')) {
    return 'batches'
  }
  if (pathname.startsWith('/app/timetable')) {
    return 'timetable'
  }
  if (pathname.startsWith('/app/meet')) {
    return 'googleMeet'
  }
  if (pathname.startsWith('/app/attendance')) {
    return 'attendance'
  }
  return 'dashboard'
}
