import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';

// The public site: one static HTML file per page, relative paths, built into site/ ready to copy as-is.
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: 'site',
    emptyOutDir: true,
    rollupOptions: { input: { index: resolve(import.meta.dirname, 'index.html'), forecast: resolve(import.meta.dirname, 'forecast/index.html'), methodology: resolve(import.meta.dirname, 'methodology/index.html'), archive: resolve(import.meta.dirname, 'archive/index.html') } },
  },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts' },
});
