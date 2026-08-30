import path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'

const currentFile = fileURLToPath(import.meta.url)
const currentDir = path.dirname(currentFile)

// outDir and indexHtmlPath MUST be passed explicitly: frappe-ui's buildConfig
// plugin otherwise auto-detects public/frontend, which is not where this app
// builds to.
export default defineConfig({
  server: {
    port: 8081,
    proxy: {
      '^/(app|api|assets|files)': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
    watch: {
      usePolling: true,
      interval: 1000,
    },
  },
  plugins: [
    ...frappeui({
      lucideIcons: true,
      frappeProxy: false,
      buildConfig: {
        outDir: path.resolve(currentDir, '../bb_tution_management/public/attendance_frontend'),
        indexHtmlPath: path.resolve(
          currentDir,
          '../bb_tution_management/www/attendance_manager.html',
        ),
        baseUrl: '/assets/bb_tution_management/attendance_frontend/',
        sourcemap: false,
      },
    }),
    vue(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(currentDir, 'src'),
      'feather-icons': path.resolve(currentDir, 'node_modules/feather-icons'),
    },
  },
  optimizeDeps: {
    include: ['debug', 'frappe-ui > feather-icons'],
    exclude: ['~icons'],
  },
})
