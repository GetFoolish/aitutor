import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    open: true, // automatically open browser
  },
  build: {
    outDir: 'build', // match CRA's output directory
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