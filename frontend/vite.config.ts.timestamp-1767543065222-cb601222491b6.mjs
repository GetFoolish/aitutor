// vite.config.ts
import { defineConfig } from "file:///C:/Users/lenovo/Downloads/WorkTask_aitutor/aitutor/frontend/node_modules/vite/dist/node/index.js";
import react from "file:///C:/Users/lenovo/Downloads/WorkTask_aitutor/aitutor/frontend/node_modules/@vitejs/plugin-react/dist/index.js";
import path from "path";
import tailwindcss from "file:///C:/Users/lenovo/Downloads/WorkTask_aitutor/aitutor/frontend/node_modules/@tailwindcss/vite/dist/index.mjs";
var __vite_injected_original_dirname = "C:\\Users\\lenovo\\Downloads\\WorkTask_aitutor\\aitutor\\frontend";
var vite_config_default = defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3e3,
    strictPort: true,
    // Fail if port 3000 is already in use instead of trying next available port
    open: true
    // automatically open browser
  },
  build: {
    outDir: "build",
    // match CRA's output directory
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          genai: ["@google/genai"],
          khan: [
            "@khanacademy/perseus",
            "@khanacademy/math-input",
            "@khanacademy/mathjax-renderer",
            "@khanacademy/wonder-blocks-core",
            "@khanacademy/wonder-blocks-layout"
          ]
        }
      }
    }
  },
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "./src"),
      // optional: add @ alias for src
      process: "process/browser"
    }
  },
  define: {
    "process.env": JSON.stringify({}),
    "process.platform": JSON.stringify("browser"),
    "process.version": JSON.stringify("")
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJDOlxcXFxVc2Vyc1xcXFxsZW5vdm9cXFxcRG93bmxvYWRzXFxcXFdvcmtUYXNrX2FpdHV0b3JcXFxcYWl0dXRvclxcXFxmcm9udGVuZFwiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiQzpcXFxcVXNlcnNcXFxcbGVub3ZvXFxcXERvd25sb2Fkc1xcXFxXb3JrVGFza19haXR1dG9yXFxcXGFpdHV0b3JcXFxcZnJvbnRlbmRcXFxcdml0ZS5jb25maWcudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0M6L1VzZXJzL2xlbm92by9Eb3dubG9hZHMvV29ya1Rhc2tfYWl0dXRvci9haXR1dG9yL2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcclxuaW1wb3J0IHJlYWN0IGZyb20gJ0B2aXRlanMvcGx1Z2luLXJlYWN0J1xyXG5pbXBvcnQgcGF0aCBmcm9tICdwYXRoJ1xyXG5pbXBvcnQgdGFpbHdpbmRjc3MgZnJvbSAnQHRhaWx3aW5kY3NzL3ZpdGUnXHJcblxyXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xyXG4gIHBsdWdpbnM6IFtyZWFjdCgpLCB0YWlsd2luZGNzcygpXSxcclxuICBzZXJ2ZXI6IHtcclxuICAgIHBvcnQ6IDMwMDAsXHJcbiAgICBzdHJpY3RQb3J0OiB0cnVlLCAvLyBGYWlsIGlmIHBvcnQgMzAwMCBpcyBhbHJlYWR5IGluIHVzZSBpbnN0ZWFkIG9mIHRyeWluZyBuZXh0IGF2YWlsYWJsZSBwb3J0XHJcbiAgICBvcGVuOiB0cnVlLCAvLyBhdXRvbWF0aWNhbGx5IG9wZW4gYnJvd3NlclxyXG4gIH0sXHJcbiAgYnVpbGQ6IHtcclxuICAgIG91dERpcjogJ2J1aWxkJywgLy8gbWF0Y2ggQ1JBJ3Mgb3V0cHV0IGRpcmVjdG9yeVxyXG4gICAgbWluaWZ5OiAndGVyc2VyJyxcclxuICAgIHRlcnNlck9wdGlvbnM6IHtcclxuICAgICAgY29tcHJlc3M6IHtcclxuICAgICAgICBkcm9wX2NvbnNvbGU6IHRydWUsXHJcbiAgICAgICAgZHJvcF9kZWJ1Z2dlcjogdHJ1ZSxcclxuICAgICAgfSxcclxuICAgIH0sXHJcbiAgICByb2xsdXBPcHRpb25zOiB7XHJcbiAgICAgIG91dHB1dDoge1xyXG4gICAgICAgIG1hbnVhbENodW5rczoge1xyXG4gICAgICAgICAgdmVuZG9yOiBbJ3JlYWN0JywgJ3JlYWN0LWRvbScsICdyZWFjdC1yb3V0ZXItZG9tJ10sXHJcbiAgICAgICAgICBnZW5haTogWydAZ29vZ2xlL2dlbmFpJ10sXHJcbiAgICAgICAgICBraGFuOiBbXHJcbiAgICAgICAgICAgICdAa2hhbmFjYWRlbXkvcGVyc2V1cycsXHJcbiAgICAgICAgICAgICdAa2hhbmFjYWRlbXkvbWF0aC1pbnB1dCcsXHJcbiAgICAgICAgICAgICdAa2hhbmFjYWRlbXkvbWF0aGpheC1yZW5kZXJlcicsXHJcbiAgICAgICAgICAgICdAa2hhbmFjYWRlbXkvd29uZGVyLWJsb2Nrcy1jb3JlJyxcclxuICAgICAgICAgICAgJ0BraGFuYWNhZGVteS93b25kZXItYmxvY2tzLWxheW91dCcsXHJcbiAgICAgICAgICBdLFxyXG4gICAgICAgIH0sXHJcbiAgICAgIH0sXHJcbiAgICB9LFxyXG4gIH0sXHJcbiAgcmVzb2x2ZToge1xyXG4gICAgYWxpYXM6IHtcclxuICAgICAgJ0AnOiBwYXRoLnJlc29sdmUoX19kaXJuYW1lLCAnLi9zcmMnKSwgLy8gb3B0aW9uYWw6IGFkZCBAIGFsaWFzIGZvciBzcmNcclxuICAgICAgcHJvY2VzczogXCJwcm9jZXNzL2Jyb3dzZXJcIlxyXG4gICAgfSxcclxuICB9LFxyXG4gIGRlZmluZToge1xyXG4gICAgJ3Byb2Nlc3MuZW52JzogSlNPTi5zdHJpbmdpZnkoe30pLFxyXG4gICAgJ3Byb2Nlc3MucGxhdGZvcm0nOiBKU09OLnN0cmluZ2lmeSgnYnJvd3NlcicpLFxyXG4gICAgJ3Byb2Nlc3MudmVyc2lvbic6IEpTT04uc3RyaW5naWZ5KCcnKSxcclxuICB9XHJcbn0pIl0sCiAgIm1hcHBpbmdzIjogIjtBQUFpWCxTQUFTLG9CQUFvQjtBQUM5WSxPQUFPLFdBQVc7QUFDbEIsT0FBTyxVQUFVO0FBQ2pCLE9BQU8saUJBQWlCO0FBSHhCLElBQU0sbUNBQW1DO0FBS3pDLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxNQUFNLEdBQUcsWUFBWSxDQUFDO0FBQUEsRUFDaEMsUUFBUTtBQUFBLElBQ04sTUFBTTtBQUFBLElBQ04sWUFBWTtBQUFBO0FBQUEsSUFDWixNQUFNO0FBQUE7QUFBQSxFQUNSO0FBQUEsRUFDQSxPQUFPO0FBQUEsSUFDTCxRQUFRO0FBQUE7QUFBQSxJQUNSLFFBQVE7QUFBQSxJQUNSLGVBQWU7QUFBQSxNQUNiLFVBQVU7QUFBQSxRQUNSLGNBQWM7QUFBQSxRQUNkLGVBQWU7QUFBQSxNQUNqQjtBQUFBLElBQ0Y7QUFBQSxJQUNBLGVBQWU7QUFBQSxNQUNiLFFBQVE7QUFBQSxRQUNOLGNBQWM7QUFBQSxVQUNaLFFBQVEsQ0FBQyxTQUFTLGFBQWEsa0JBQWtCO0FBQUEsVUFDakQsT0FBTyxDQUFDLGVBQWU7QUFBQSxVQUN2QixNQUFNO0FBQUEsWUFDSjtBQUFBLFlBQ0E7QUFBQSxZQUNBO0FBQUEsWUFDQTtBQUFBLFlBQ0E7QUFBQSxVQUNGO0FBQUEsUUFDRjtBQUFBLE1BQ0Y7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsU0FBUztBQUFBLElBQ1AsT0FBTztBQUFBLE1BQ0wsS0FBSyxLQUFLLFFBQVEsa0NBQVcsT0FBTztBQUFBO0FBQUEsTUFDcEMsU0FBUztBQUFBLElBQ1g7QUFBQSxFQUNGO0FBQUEsRUFDQSxRQUFRO0FBQUEsSUFDTixlQUFlLEtBQUssVUFBVSxDQUFDLENBQUM7QUFBQSxJQUNoQyxvQkFBb0IsS0FBSyxVQUFVLFNBQVM7QUFBQSxJQUM1QyxtQkFBbUIsS0FBSyxVQUFVLEVBQUU7QUFBQSxFQUN0QztBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
