import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: false,
    open: false,
    headers: {
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
    },
    // Reduce HMR noise: debounce rapid cascading updates (Bug #34)
    hmr: {
      overlay: true,
    },
    watch: {
      // Avoid polling (default); only re-trigger on actual file writes
      usePolling: false,
      // Ignore large generated/static directories that never need HMR
      ignored: ['**/node_modules/**', '**/build/**', '**/.git/**'],
    },
  },
  build: {
    outDir: 'build', // match CRA's output directory
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          genai: ['@google/genai'],
          khan: [
            '@khanacademy/perseus',
            '@khanacademy/math-input',
            '@khanacademy/mathjax-renderer',
            '@khanacademy/wonder-blocks-core',
            '@khanacademy/wonder-blocks-layout',
          ],
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'), // optional: add @ alias for src
      process: "process/browser"
    },
  },
  define: {
    'process.env': JSON.stringify({}),
    'process.platform': JSON.stringify('browser'),
    'process.version': JSON.stringify(''),
  }
})