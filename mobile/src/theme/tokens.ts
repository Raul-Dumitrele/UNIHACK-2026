// Same values as tailwind.config.js and web/src/theme/tokens.ts.
// Use these where className can't reach (tab bar, icons, map markers).
export const colors = {
  primary: '#2f6f4f',
  background: '#f7f7f5',
  card: '#ffffff',
  foreground: '#1d1d1b',
  muted: '#6b6b66',
  border: '#e2e2dc',
  success: '#2f8f4f',
  destructive: '#b3261e',
  demo: '#b86b00',
} as const

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const
export const radius = { sm: 8, md: 12, lg: 16, pill: 999 } as const
