import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/datasets': 'http://127.0.0.1:8000',
      '/runs': 'http://127.0.0.1:8000',
      '/demo': 'http://127.0.0.1:8000',
      '/audit': 'http://127.0.0.1:8000',
      '/benchmarks': 'http://127.0.0.1:8000',
      '/adversarial': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/metrics': 'http://127.0.0.1:8000',
    },
  },
});
