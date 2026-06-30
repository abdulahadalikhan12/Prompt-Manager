import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Three proxy rules now -- /chats joins /prompts since chats also live
// in prompt-service (port 8000), just a different path prefix. Only
// affects `npm run dev`; in production nginx performs this same split
// (see nginx.conf at the repo root).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/prompts': 'http://127.0.0.1:8000',
      '/chats': 'http://127.0.0.1:8000',
      '/reviews': 'http://127.0.0.1:8001',
    },
  },
})
