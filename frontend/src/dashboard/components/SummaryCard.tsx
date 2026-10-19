import { Card, CardActionArea, CardContent, CircularProgress, Stack, Typography } from '@mui/material'
import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { Link as RouterLink } from 'react-router-dom'

import type { SummaryMetric } from '../metrics'

export function SummaryCard({ metric }: { metric: SummaryMetric }) {
  const { t } = useTranslation('dashboard')
  const titleId = useId()
  const label = t(`cards.${metric.id}`)
  const linked = metric.status === 'ready' && typeof metric.value === 'number' && Boolean(metric.href)
  const content = (
    <CardContent>
      <Typography id={titleId} variant="body2" color="text.secondary">
        {label}
      </Typography>
      <MetricValue metric={metric} />
    </CardContent>
  )

  return (
    <Card component="section" aria-labelledby={titleId} variant="outlined" sx={{ height: '100%' }}>
      {linked ? (
        <CardActionArea component={RouterLink} to={metric.href ?? '/app'} sx={{ height: '100%' }}>
          {content}
        </CardActionArea>
      ) : (
        content
      )}
    </Card>
  )
}

function MetricValue({ metric }: { metric: SummaryMetric }) {
  const { t } = useTranslation('dashboard')

  if (metric.status === 'loading') {
    return (
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.5 }} role="status">
        <CircularProgress size={22} aria-hidden />
        <Typography color="text.secondary">{t('loadingMetrics')}</Typography>
      </Stack>
    )
  }

  if (metric.status === 'ready' && typeof metric.value === 'number') {
    return (
      <Typography component="p" sx={{ mt: 1, fontSize: '2rem', fontWeight: 700, lineHeight: 1.2 }}>
        {metric.value}
      </Typography>
    )
  }

  const message =
    metric.status === 'error' ? t('loadError') : metric.status === 'empty' ? t('empty') : t('notAvailable')

  return (
    <Typography color="text.secondary" sx={{ mt: 1.5 }}>
      {message}
    </Typography>
  )
}
