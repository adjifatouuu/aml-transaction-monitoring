/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
        risk: {
          critique: { DEFAULT: '#dc2626', bg: '#fef2f2', border: '#fca5a5' },
          high:     { DEFAULT: '#ea580c', bg: '#fff7ed', border: '#fdba74' },
          medium:   { DEFAULT: '#ca8a04', bg: '#fefce8', border: '#fde047' },
          low:      { DEFAULT: '#16a34a', bg: '#f0fdf4', border: '#86efac' },
        },
        surface: {
          sidebar: '#1e293b',
          card:    '#ffffff',
          page:    '#f8fafc',
        },
      },
      boxShadow: {
        card:       '0 1px 3px 0 rgba(0,0,0,0.07), 0 1px 2px -1px rgba(0,0,0,0.05)',
        'card-hover': '0 4px 6px -1px rgba(0,0,0,0.08), 0 2px 4px -2px rgba(0,0,0,0.05)',
      },
      borderRadius: {
        card: '0.75rem',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
};
