import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Two separate proxy rules -- one per backend service -- because this
// frontend talks to TWO independent FastAPI services, unlike the
// single-backend notes app. Only affects `npm run dev`; in production
// nginx performs this same split (see nginx.conf at the repo root).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/prompts': 'http://127.0.0.1:8000',
      '/reviews': 'http://127.0.0.1:8001',
    },
  },
})
