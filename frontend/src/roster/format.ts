export function formatClock(value: string | null | undefined) {
  if (!value) {
    return ''
  }
  const match = /^(\d{2}):(\d{2})/.exec(value)
  if (!match) {
    return value
  }
  return `${match[1]}:${match[2]}`
}

export function formatDisplayDate(value: string | null | undefined) {
  if (!value) {
    return ''
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) {
    return value
  }
  return `${match[3]}/${match[2]}/${match[1]}`
}

export function isIsoDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false
  }
  const [year, month, day] = value.split('-').map(Number)
  const parsed = new Date(Date.UTC(year, month - 1, day))
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day
}

export function isMobileNumber(value: string) {
  return /^(?:\+91|91|0)?[6-9]\d{9}$/.test(value.replace(/[\s\-()]/g, ''))
}
