/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,vue}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        base: {
          900: '#0a0a0f',
          800: '#0f0f17',
          700: '#13131a',
          600: '#1a1a24',
          500: '#22222e',
          400: '#2a2a38',
        },
        accent: {
          cyan: '#00d4ff',
          amber: '#f59e0b',
          violet: '#a855f7',
          green: '#10b981',
          red: '#ef4444',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-glow': 'pulse-glow 1.5s ease-in-out infinite',
        'flow-dash': 'flow-dash 0.8s linear infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 8px rgba(0, 212, 255, 0.4)' },
          '50%': { boxShadow: '0 0 24px rgba(0, 212, 255, 0.8)' },
        },
        'flow-dash': {
          to: { strokeDashoffset: '-16' },
        },
      },
    },
  },
  plugins: [],
}
