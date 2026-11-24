/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: '#172B3A', 700: '#1E3646' },
        deep: '#29465B',
        teal: { DEFAULT: '#477A78', 50: '#EEF4F3', 100: '#DCE9E7', 700: '#3A6563' },
        sage: { DEFAULT: '#81968B', 50: '#F1F4F2' },
        ivory: '#F6F5F0',
        bronze: { DEFAULT: '#AD9063', 50: '#F7F2EA' },
        ink: '#28343C',
        muted: '#697780',
        line: '#E2E6E3',
        warn: { DEFAULT: '#B78B48', 50: '#F8F1E5', 700: '#8A6630' },
        danger: { DEFAULT: '#A65D5D', 50: '#F6ECEC', 700: '#8A4747' },
        success: { DEFAULT: '#648573', 50: '#EDF3EF', 700: '#4E6B5B' },
      },
      fontFamily: {
        sans: ['"Source Sans 3"', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(23,43,58,0.04), 0 2px 8px rgba(23,43,58,0.05)',
      },
      borderRadius: { xl: '0.875rem' },
    },
  },
  plugins: [],
}
