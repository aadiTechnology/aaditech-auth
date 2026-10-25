import { Box, Button, CircularProgress, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { roleLabel } from '../../access/role-label'
import { ErrorAlert } from '../../components/common/ErrorAlert'
import { MeetJoinLink } from '../../meet/components/MeetJoinLink'
import { formatClock, formatDisplayDate } from '../../roster/format'
import { useAuth } from '../../store/auth-context'
import { SummaryCard } from '../components/SummaryCard'
import { loadDashboardMetrics, type DashboardData, type UpcomingClass } from '../metrics'

function missingMeetingLink(item: UpcomingClass) {
  return item.meet_status === 'missing' || item.meet_url === null
}

export function DashboardPage() {
  const { t } = useTranslation(['dashboard', 'attendance', 'auth', 'access'])
  const { user } = useAuth()
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    let cancelled = false
    loadDashboardMetrics()
      .then((result) => {
        if (!cancelled) {
          setData(result)
          setStatus('ready')
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus('error')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const roles = user?.roles.map((role) => roleLabel(role, t)).join(', ')

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography color="text.secondary">{t('dashboard:subtitle')}</Typography>
        <Typography>{t('dashboard:signedInAs', { name: user?.full_name ?? '' })}</Typography>
        {roles ? (
          <Typography color="text.secondary">
            {t('auth:currentRole')}: {roles}
          </Typography>
        ) : null}
      </Stack>

      <Typography variant="h2">{t('dashboard:metricsHeading')}</Typography>

      {status === 'loading' ? (
        <Stack direction="row" spacing={1} alignItems="center" role="status">
          <CircularProgress size={22} aria-hidden />
          <Typography>{t('dashboard:loadingMetrics')}</Typography>
        </Stack>
      ) : null}

      {status === 'error' ? <ErrorAlert message={t('dashboard:loadError')} /> : null}

      {status === 'ready' && data && data.metrics.length === 0 ? (
        <Typography>{t('dashboard:emptyMetrics')}</Typography>
      ) : null}

      {status === 'ready' && data && data.metrics.length > 0 ? (
        <Box
          sx={{
            display: 'grid',
            gap: 2,
            gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', lg: 'repeat(4, 1fr)' },
          }}
        >
          {data.metrics.map((metric) => (
            <SummaryCard key={metric.id} metric={metric} />
          ))}
        </Box>
      ) : null}

      {status === 'ready' && data ? (
        <Stack spacing={1.5}>
          <Typography variant="h2">{t('dashboard:upcomingHeading')}</Typography>
          {data.upcomingStatus === 'ready'
            ? data.upcoming.map((item) => (
                <Button
                  key={item.id}
                  component={Link}
                  to={`/app/timetable?date=${item.class_date}`}
                  sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                >
                  {t('dashboard:classLink', {
                    date: formatDisplayDate(item.class_date),
                    time: `${formatClock(item.start_time)}–${formatClock(item.end_time)}`,
                    batch: item.topic ? `${item.batch_name} — ${item.topic}` : item.batch_name,
                  })}
                </Button>
              ))
            : null}
          {data.upcomingStatus === 'empty' ? <Typography>{t('dashboard:upcomingEmpty')}</Typography> : null}
          {data.upcomingStatus === 'unavailable' ? (
            <Typography color="text.secondary">{t('dashboard:upcomingUnavailable')}</Typography>
          ) : null}
          {data.upcomingStatus === 'error' ? <ErrorAlert message={t('dashboard:upcomingError')} /> : null}
        </Stack>
      ) : null}

      {status === 'ready' && data ? (
        <Stack spacing={1.5}>
          <Typography variant="h2">{t('dashboard:todayHeading')}</Typography>
          {data.todayStatus === 'ready'
            ? data.todayClasses.map((item) => (
                <Stack key={item.id} spacing={0.5}>
                  <Button
                    component={Link}
                    to={`/app/timetable?date=${item.class_date}`}
                    sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                  >
                    {t('dashboard:classLink', {
                      date: formatDisplayDate(item.class_date),
                      time: `${formatClock(item.start_time)}–${formatClock(item.end_time)}`,
                      batch: item.topic ? `${item.batch_name} — ${item.topic}` : item.batch_name,
                    })}
                  </Button>
                  {item.meet_status || item.meet_url !== undefined ? (
                    <Typography variant="body2">
                      {missingMeetingLink(item) ? t('dashboard:linkMissing') : t('dashboard:linkAdded')}
                    </Typography>
                  ) : null}
                  <MeetJoinLink url={item.meet_url} label={t('dashboard:joinMeeting')} />
                </Stack>
              ))
            : null}
          {data.todayStatus === 'empty' ? <Typography>{t('dashboard:todayEmpty')}</Typography> : null}
          {data.todayStatus === 'unavailable' ? (
            <Typography color="text.secondary">{t('dashboard:todayUnavailable')}</Typography>
          ) : null}
          {data.todayStatus === 'error' ? <ErrorAlert message={t('dashboard:todayError')} /> : null}
          {data.todayStatus === 'ready' && data.todayClasses.filter(missingMeetingLink).length > 0 ? (
            <Typography>
              {t('dashboard:missingLinks', { count: data.todayClasses.filter(missingMeetingLink).length })}
            </Typography>
          ) : null}

          <Typography variant="h2">{t('dashboard:attendanceHeading')}</Typography>
          {data.attendanceTodayStatus === 'ready'
            ? data.attendanceToday.map((item) => (
                <Button
                  key={item.id}
                  component={Link}
                  to={`/app/attendance?batch=${item.batch_id}&class=${item.id}`}
                  sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                >
                  {t('dashboard:attendanceLink', {
                    batch: item.batch_name,
                    time: `${formatClock(item.start_time)}–${formatClock(item.end_time)}`,
                    status: t(`attendance:completion.${item.completion}`),
                  })}
                </Button>
              ))
            : null}
          {data.attendanceTodayStatus === 'empty' ? <Typography>{t('dashboard:attendanceEmpty')}</Typography> : null}
          {data.attendanceTodayStatus === 'unavailable' ? (
            <Typography color="text.secondary">{t('dashboard:attendanceUnavailable')}</Typography>
          ) : null}
          {data.attendanceTodayStatus === 'error' ? <ErrorAlert message={t('dashboard:attendanceError')} /> : null}
        </Stack>
      ) : null}
    </Stack>
  )
}
