/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      boxShadow: {
        'glow': '0 0 15px rgba(255, 255, 255, 0.1)',
        'glow-white': '0 0 20px rgba(255, 255, 255, 0.2)',
      },
      borderColor: {
        'white-10': 'rgba(255, 255, 255, 0.1)',
        'white-20': 'rgba(255, 255, 255, 0.2)',
      }
    },
  },
  plugins: [],
}

