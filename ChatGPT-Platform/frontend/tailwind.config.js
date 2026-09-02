/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        chatgpt: {
          bg: '#212121',
          main: '#171717',
          sidebar: '#171717',
          sidebarDark: '#121212',
          card: '#2f2f2f',
          userBubble: '#2f2f2f',
          inputBg: '#2f2f2f',
          border: '#3c3c3c',
          green: '#10a37f',
          greenHover: '#1a7f64',
          accent: '#10a37f',
          muted: '#8e8ea0',
          darkBorder: '#2f2f2f',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['Fira Code', 'Cascadia Code', 'JetBrains Mono', 'Consolas', 'monospace']
      }
    },
  },
  plugins: [],
}
