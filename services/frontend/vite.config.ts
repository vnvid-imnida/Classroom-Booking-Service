import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

/** ngrok / Cloudflare Tunnel hostnames for public site URL in dev */
const NGROK_ALLOWED_HOSTS = [
  '.ngrok-free.dev',
  '.ngrok-free.app',
  '.ngrok.io',
  '.ngrok.app',
];

/** Quick check that ngrok tunnels port 5173 (not backend :8083). */
function devHealthPlugin(): Plugin {
  return {
    name: 'dev-health',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const path = req.url?.split('?')[0];
        if (path === '/__health') {
          res.setHeader('Content-Type', 'application/json');
          res.end(
            JSON.stringify({
              ok: true,
              service: 'spbpu-booking-frontend',
              routes: ['/login', '/register'],
              vite: 'dev',
              hint: 'ngrok http 127.0.0.1:5173 → FRONTEND_URL=https://<host>',
            }),
          );
          return;
        }
        next();
      });
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig({
  base: '/',
  appType: 'spa',
  plugins: [react(), devHealthPlugin()],
  server: {
    port: 5173,
    // 127.0.0.1 avoids Windows resolving localhost → [::1] (ngrok ERR_NGROK_8012)
    host: '127.0.0.1',
    strictPort: true,
    allowedHosts: NGROK_ALLOWED_HOSTS,
    proxy: {
      // Локально: /api/* → backend:8083 (без CORS, работает с localhost и LAN IP)
      '/api': {
        target: 'http://127.0.0.1:8083',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 5173,
    host: '127.0.0.1',
    strictPort: true,
    allowedHosts: NGROK_ALLOWED_HOSTS,
  },
});
