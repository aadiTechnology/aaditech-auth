const CODE = /^[a-z]{3}-[a-z]{4}-[a-z]{3}$/
const LOOKUP = /^[A-Za-z0-9_-]{10,64}$/
const QUERY_KEY = /^[A-Za-z][A-Za-z0-9_-]{0,20}$/
const QUERY_VALUE = /^[A-Za-z0-9._~-]{0,64}$/
const BLOCKED_QUERY = new Set(['continue', 'redirect', 'url', 'next', 'q', 'dest'])

function invalid(): never {
  throw new Error('invalid')
}

/** Returns a canonical HTTPS Google Meet URL, or throws when the value is unsafe. */
export function normalizeMeetUrl(value: string) {
  const raw = value.trim()
  if (!raw || raw.length > 300 || [...raw].some((character) => character.charCodeAt(0) < 32 || character === '\\' || /\s/.test(character))) {
    invalid()
  }
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    invalid()
  }
  if (url.protocol !== 'https:' || url.hostname !== 'meet.google.com') {
    invalid()
  }
  if (url.username || url.password || url.hash || (url.port !== '' && url.port !== '443')) {
    invalid()
  }
  const trimmed = url.pathname.replace(/\/+$/, '') || '/'
  const segments = trimmed.split('/').filter(Boolean)
  if (trimmed !== `/${segments.join('/')}`) {
    invalid()
  }
  let path = ''
  if (segments.length === 1 && CODE.test(segments[0].toLowerCase())) {
    path = segments[0].toLowerCase()
  } else if (segments.length === 2 && segments[0].toLowerCase() === 'lookup' && LOOKUP.test(segments[1])) {
    path = `lookup/${segments[1]}`
  } else {
    invalid()
  }
  const params = [...url.searchParams.entries()]
  if (params.length > 6) {
    invalid()
  }
  for (const [key, item] of params) {
    if (BLOCKED_QUERY.has(key.toLowerCase()) || !QUERY_KEY.test(key) || !QUERY_VALUE.test(item)) {
      invalid()
    }
  }
  const query = params.length > 0 ? `?${new URLSearchParams(params).toString()}` : ''
  const canonical = `https://meet.google.com/${path}${query}`
  if (canonical.length > 300) {
    invalid()
  }
  return canonical
}

/** Returns a URL that is safe to open, or null. */
export function safeMeetHref(value: string | null | undefined) {
  if (!value) {
    return null
  }
  try {
    return normalizeMeetUrl(value)
  } catch {
    return null
  }
}
