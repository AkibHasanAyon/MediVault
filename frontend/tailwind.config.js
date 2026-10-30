/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        medivault: {
          primary: '#087E8B',
          navy: '#16324F',
          accent: '#2A9D8F',
          danger: '#E76F51',
          warning: '#F4A261',
          bg: '#F8FAFC',
          card: '#FFFFFF',
          border: '#E2E8F0',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans Bengali', 'system-ui', 'sans-serif'],
        bengali: ['Noto Sans Bengali', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

