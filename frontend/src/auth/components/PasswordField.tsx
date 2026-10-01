import Visibility from '@mui/icons-material/Visibility'
import VisibilityOff from '@mui/icons-material/VisibilityOff'
import { IconButton, InputAdornment, TextField } from '@mui/material'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

interface PasswordFieldProps {
  id: string
  label: string
  value: string
  autoComplete: string
  error?: string
  disabled?: boolean
  onChange: (value: string) => void
}

export function PasswordField({
  id,
  label,
  value,
  autoComplete,
  error,
  disabled,
  onChange,
}: PasswordFieldProps) {
  const { t } = useTranslation('auth')
  const [visible, setVisible] = useState(false)

  return (
    <TextField
      id={id}
      name={id}
      label={label}
      type={visible ? 'text' : 'password'}
      autoComplete={autoComplete}
      value={value}
      required
      fullWidth
      disabled={disabled}
      error={Boolean(error)}
      helperText={error}
      onChange={(event) => onChange(event.target.value)}
      slotProps={{
        input: {
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                aria-label={visible ? t('hidePassword') : t('showPassword')}
                aria-pressed={visible}
                onClick={() => setVisible((current) => !current)}
                edge="end"
              >
                {visible ? <VisibilityOff /> : <Visibility />}
              </IconButton>
            </InputAdornment>
          ),
        },
      }}
    />
  )
}
