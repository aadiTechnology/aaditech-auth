import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { theme } from '../../theme/theme'
import { SummaryCard } from './SummaryCard'
import type { SummaryMetric } from '../metrics'

function renderCard(metric: SummaryMetric) {
  return render(
    <ThemeProvider theme={theme}>
      <SummaryCard metric={metric} />
    </ThemeProvider>,
  )
}

describe('SummaryCard', () => {
  it('shows a placeholder instead of a number when the metric is unavailable', () => {
    renderCard({ id: 'students', status: 'unavailable', value: null })
    expect(screen.getByRole('region', { name: 'Total Students' })).toHaveTextContent('Not available yet')
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('shows a number only when the metric is ready', () => {
    renderCard({ id: 'batches', status: 'ready', value: 4 })
    expect(screen.getByRole('region', { name: 'Total Batches' })).toHaveTextContent('4')
  })

  it('shows loading, empty, and error messages', () => {
    const { rerender } = renderCard({ id: 'todayClasses', status: 'loading', value: null })
    expect(screen.getByText('Loading summary')).toBeInTheDocument()

    rerender(
      <ThemeProvider theme={theme}>
        <SummaryCard metric={{ id: 'todayClasses', status: 'empty', value: null }} />
      </ThemeProvider>,
    )
    expect(screen.getByText('No records yet')).toBeInTheDocument()

    rerender(
      <ThemeProvider theme={theme}>
        <SummaryCard metric={{ id: 'pendingFees', status: 'error', value: null }} />
      </ThemeProvider>,
    )
    expect(screen.getByRole('region', { name: 'Pending Fees' })).toHaveTextContent(
      'This summary could not be loaded.',
    )
  })
})
