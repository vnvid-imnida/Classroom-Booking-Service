import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      // Локально: /api/* → backend:8083 (без CORS, работает с localhost и LAN IP)
      '/api': {
        target: 'http://127.0.0.1:8083',
        changeOrigin: true,
      },
    },
  },
});
