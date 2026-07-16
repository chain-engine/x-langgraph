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
          900: '#f8fafc',
          800: '#f1f5f9',
          700: '#e2e8f0',
          600: '#cbd5e1',
          500: '#94a3b8',
          400: '#64748b',
        },
        accent: {
          cyan: '#0ea5e9',
          amber: '#f59e0b',
          violet: '#8b5cf6',
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
          '0%, 100%': { boxShadow: '0 0 8px rgba(14, 165, 233, 0.4)' },
          '50%': { boxShadow: '0 0 24px rgba(14, 165, 233, 0.6)' },
        },
        'flow-dash': {
          to: { strokeDashoffset: '-16' },
        },
      },
    },
  },
  plugins: [],
}
