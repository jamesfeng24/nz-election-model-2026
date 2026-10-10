import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';

// SITE_ARCHIVE_DATE=YYYY-MM-DD builds the frozen copy that is served from archive/<date>/ (banner and links back to
// the live site); SITE_OUT_DIR changes the output folder. Without them this is the live site in site/.
const archiveDate = process.env.SITE_ARCHIVE_DATE ?? '';
if (archiveDate && !/^\d{4}-\d{2}-\d{2}$/.test(archiveDate)) throw new Error('SITE_ARCHIVE_DATE must be YYYY-MM-DD');

// The public site: one static HTML file per page, relative paths, built into site/ ready to copy as-is.
export default defineConfig({
  base: './',
  define: { __ARCHIVE_DATE__: JSON.stringify(archiveDate) },
  plugins: [react()],
  build: {
    outDir: process.env.SITE_OUT_DIR ?? 'site',
    emptyOutDir: true,
    rollupOptions: { input: { index: resolve(import.meta.dirname, 'index.html'), forecast: resolve(import.meta.dirname, 'forecast/index.html'), electorates: resolve(import.meta.dirname, 'electorates/index.html'), polls: resolve(import.meta.dirname, 'polls/index.html'), methodology: resolve(import.meta.dirname, 'methodology/index.html'), archive: resolve(import.meta.dirname, 'archive/index.html'), about: resolve(import.meta.dirname, 'about/index.html') } },
  },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts' },
});
