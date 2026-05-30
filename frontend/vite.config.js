import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/brief': 'http://127.0.0.1:8000',
      '/signals': 'http://127.0.0.1:8000',
      '/compare': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/cache': 'http://127.0.0.1:8000'
    }
  }
})
