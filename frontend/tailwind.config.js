/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#6366f1',
        'stress-low': '#22c55e',
        'stress-mid': '#f59e0b',
        'stress-high': '#ef4444',
      },
    },
  },
  plugins: [],
}
