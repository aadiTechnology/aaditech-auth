import { Alert } from '@mui/material'

export function ErrorAlert({ message }: { message: string }) {
  return (
    <Alert severity="error" role="alert">
      {message}
    </Alert>
  )
}
