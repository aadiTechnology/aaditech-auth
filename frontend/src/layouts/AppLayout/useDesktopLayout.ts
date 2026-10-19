import { useEffect, useState } from 'react'

const DESKTOP_QUERY = '(min-width: 900px)'

function matchesDesktop() {
  if (typeof window.matchMedia !== 'function') {
    return true
  }
  return window.matchMedia(DESKTOP_QUERY).matches
}

export function useDesktopLayout() {
  const [desktop, setDesktop] = useState(matchesDesktop)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') {
      return
    }
    const media = window.matchMedia(DESKTOP_QUERY)
    const update = () => setDesktop(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  return desktop
}
