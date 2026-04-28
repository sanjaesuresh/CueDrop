import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      '/health': 'http://localhost:8000',
      '/queue': 'http://localhost:8000',
      '/request': 'http://localhost:8000',
      '/skip': 'http://localhost:8000',
      '/tick': 'http://localhost:8000',
      '/status': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/requests': 'http://localhost:8000',
      '/approve': 'http://localhost:8000',
      '/decline': 'http://localhost:8000',
      '/session': 'http://localhost:8000',
      '/settings': 'http://localhost:8000',
      '/search': 'http://localhost:8000',
      '/learn': 'http://localhost:8000',
      '/scrape': 'http://localhost:8000',
    },
  },
});
