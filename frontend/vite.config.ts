import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The FastAPI server (docs/05 §10). The dev server proxies API and health requests to it,
// so the browser talks to one origin; set APP_ORIGIN=http://localhost:5173 while using it.
const api = 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': api,
      '/healthz': api,
      '/readyz': api,
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
  },
})
