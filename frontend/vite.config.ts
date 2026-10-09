/// <reference types="vitest/config" />
import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  // 환경변수는 프로젝트 루트의 .env 하나만 사용한다 (VITE_ 접두사만 번들에 노출).
  envDir: path.resolve(__dirname, '..'),
  server: { port: 5173 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    env: { VITE_API_BASE_URL: 'http://api.test/api/v1' },
  },
});
