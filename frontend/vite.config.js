import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Three proxy rules now -- /chats joins /prompts since chats also live
// in prompt-service (port 8000), just a different path prefix. Only
// affects `npm run dev`; in production nginx performs this same split
// (see nginx.conf at the repo root).
export default defineConfig({
  plugins: [react()],
  server: {
    // nginx + ngrok pass the public Host header through to Vite
    allowedHosts: ['.ngrok-free.dev', '.ngrok-free.app', '.ngrok.app', '.ngrok.io'],
    // HMR over ngrok HTTPS (browser must connect via wss on 443, not localhost)
    hmr: {
      clientPort: 443,
      protocol: 'wss',
    },
    proxy: {
      '/prompts': 'http://127.0.0.1:8000',
      '/chats': 'http://127.0.0.1:8000',
      '/reviews': 'http://127.0.0.1:8001',
      '/documents': 'http://127.0.0.1:8003',
    },
  },
})
