/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#dce6ff',
          500: '#4f6ef7',
          600: '#3b5af0',
          700: '#2d47d6',
        },
      },
    },
  },
  plugins: [],
}
