import frappeuiTailwind from 'frappe-ui/tailwind'

export default {
  presets: [frappeuiTailwind],
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fffdf0',
          100: '#fff9d1',
          400: '#ffe45e',
          500: '#FFD700',
          600: '#e6c200',
          700: '#b39600',
        },
      },
    },
  },
  plugins: [],
}
