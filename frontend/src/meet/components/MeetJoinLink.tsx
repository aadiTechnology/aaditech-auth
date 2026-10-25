import { Button } from '@mui/material'

import { safeMeetHref } from '../url'

export function MeetJoinLink({ url, label }: { url: string | null | undefined; label: string }) {
  const href = safeMeetHref(url)
  if (!href) {
    return null
  }
  return (
    <Button component="a" href={href} target="_blank" rel="noopener noreferrer" size="small" variant="contained">
      {label}
    </Button>
  )
}
