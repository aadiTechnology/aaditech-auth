export const COACHING_TIME_ZONE = 'Asia/Kolkata'

export function coachingToday(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: COACHING_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now)
}

export function addDays(isoDate: string, days: number) {
  const [year, month, day] = isoDate.split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function startOfWeek(isoDate: string) {
  const [year, month, day] = isoDate.split('-').map(Number)
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay()
  const delta = weekday === 0 ? -6 : 1 - weekday
  return addDays(isoDate, delta)
}

export function weekDates(weekStart: string) {
  return Array.from({ length: 7 }, (_, index) => addDays(weekStart, index))
}

export function withSeconds(value: string) {
  if (/^\d{2}:\d{2}$/.test(value)) {
    return `${value}:00`
  }
  return value
}
