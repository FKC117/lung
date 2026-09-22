import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // Django validates the Origin header on session-authenticated writes.
        // During Vite development, make the proxied request same-origin to Django.
        headers: { origin: 'http://127.0.0.1:8000' },
      },
      '/admin': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        headers: { origin: 'http://127.0.0.1:8000' },
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
  },
})
