import { describe, expect, it } from 'vitest'

import { normalizeMeetUrl, safeMeetHref } from './url'

describe('Google Meet URLs', () => {
  it('accepts meeting codes, lookup links, and a trailing slash', () => {
    expect(normalizeMeetUrl('https://meet.google.com/abc-defg-hij')).toBe('https://meet.google.com/abc-defg-hij')
    expect(normalizeMeetUrl('https://meet.google.com/ABC-DEFG-HIJ/')).toBe('https://meet.google.com/abc-defg-hij')
    expect(normalizeMeetUrl('https://meet.google.com/abc-defg-hij?authuser=0')).toBe(
      'https://meet.google.com/abc-defg-hij?authuser=0',
    )
    expect(normalizeMeetUrl('https://meet.google.com/lookup/abcdefghij')).toBe(
      'https://meet.google.com/lookup/abcdefghij',
    )
  })

  it('rejects unsafe or non-Meet destinations', () => {
    for (const value of [
      'http://meet.google.com/abc-defg-hij',
      'https://evil.example/abc-defg-hij',
      'https://meet.google.com.evil.example/abc-defg-hij',
      'javascript:https://meet.google.com/abc-defg-hij',
      'https://meet.google.com/new',
      'https://user:pass@meet.google.com/abc-defg-hij',
      'https://meet.google.com/abc-defg-hij?redirect=https://evil.example',
    ]) {
      expect(safeMeetHref(value)).toBeNull()
    }
  })
})
