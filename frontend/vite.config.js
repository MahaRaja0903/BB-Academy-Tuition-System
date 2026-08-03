import path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'

const currentFile = fileURLToPath(import.meta.url)
const currentDir = path.dirname(currentFile)

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    port: 8080,
    proxy: {
      '^/(app|api|assets|files)': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
    watch: {
      usePolling: true,
      interval: 1000
    }
  },
  plugins: [
    ...frappeui({
      lucideIcons: true,
      frappeProxy: false,
      buildConfig: {
        indexHtmlPath: path.resolve(currentDir, '../bb_tution_management/www/tuition_app.html'),
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
    include: [
      'debug',
      'frappe-ui > feather-icons',
      'showdown',
      'engine.io-client',
      'socket.io-client',
    ],
    exclude: ['~icons'],
  },
})
