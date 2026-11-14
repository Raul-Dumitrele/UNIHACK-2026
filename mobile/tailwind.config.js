// Colors mirror web/src/index.css and src/theme/tokens.ts. Change all three together.
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,jsx,ts,tsx}', './src/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        background: '#f7f7f5',
        foreground: '#1d1d1b',
        card: '#ffffff',
        primary: { DEFAULT: '#2f6f4f', foreground: '#ffffff' },
        secondary: { DEFAULT: '#eef2ee', foreground: '#1f3d2c' },
        muted: { DEFAULT: '#f0f0ec', foreground: '#6b6b66' },
        accent: { DEFAULT: '#e6efe9', foreground: '#1f3d2c' },
        border: '#e2e2dc',
        success: '#2f8f4f',
        destructive: '#b3261e',
        demo: { DEFAULT: '#b86b00', soft: '#fff4e0' },
      },
      borderRadius: { xl: '16px', '2xl': '20px' },
    },
  },
  plugins: [],
}
