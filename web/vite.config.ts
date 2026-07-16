import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import Inspector from 'unplugin-vue-dev-locator/vite'

export default defineConfig({
  build: {
    sourcemap: 'hidden',
  },
  plugins: [
    vue(),
    Inspector(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/workflows': 'http://localhost:8009',
      '/chat': 'http://localhost:8009',
      '/approval': 'http://localhost:8009',
      '/health': 'http://localhost:8009',
    },
  },
})
