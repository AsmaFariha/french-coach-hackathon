import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Built assets are served by app_custom.py at /custom/, so all asset URLs
// in the production build must be prefixed accordingly. The dev server
// In production, HF proxies /gradio_api/* → /* on our server (strips prefix).
// React assets live at /gradio_api/custom/* externally → /custom/* internally.
// API calls go to /gradio_api/fc/* externally → /fc/* internally.
// In dev, Vite proxy strips /gradio_api before forwarding to localhost:7861.
export default defineConfig({
  base: '/gradio_api/custom/',
  plugins: [react()],
  server: {
    proxy: {
      '/gradio_api/fc': {
        target: 'http://localhost:7861',
        rewrite: (path) => path.replace('/gradio_api', ''),
      },
    },
  },
})
