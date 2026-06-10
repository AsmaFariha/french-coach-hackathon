import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Built assets are served by app_custom.py at /custom/, so all asset URLs
// in the production build must be prefixed accordingly. The dev server
// proxies /api to the FastAPI backend (app_custom.py, port 7861) so
// `npm run dev` can hit the real API without CORS or a second build step.
export default defineConfig({
  base: '/custom/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:7861',
    },
  },
})
