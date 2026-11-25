import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// GitHub Pages sirve el sitio en /SupplySense/.
export default defineConfig({
  base: '/SupplySense/',
  plugins: [react(), tailwindcss()],
  test: { environment: 'node' },
})
