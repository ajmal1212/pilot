import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import frappeuiPlugin from 'frappe-ui/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendProxyUrl = env.BACKEND_PROXY_URL

  return {
    plugins: [
      frappeuiPlugin({
        lucideIcons: true,
        frappeProxy: false,
        jinjaBootData: false,
        buildConfig: false,
      }),
      vue(),
    ],
    build: {
      outDir: '../backend/static/dist',
      emptyOutDir: true,
      sourcemap: mode === 'development',
      minify: mode !== 'development',
      // Rolldown's CSS minifier strips @media wrappers entirely (verified
      // pre-existing on unmodified main, unrelated to plugins) - every
      // sm:/md:/lg: responsive utility ends up applying unconditionally,
      // with plain cascade order deciding the outcome instead of viewport
      // width. Keep CSS unminified until that's fixed upstream or Pilot
      // pins a different minifier.
      cssMinify: false,
      rollupOptions: {
        // Real vue/frappe-ui code lives in exactly one place: the
        // separately-built plugin-runtime/vendor.js (see
        // vite.vendor.config.js and package.json's build script). Core's
        // own app code resolves them at runtime through the import map in
        // index.html instead of bundling its own copy, so core and every
        // plugin share one literal Vue instance.
        external: ['vue', 'vue-router', 'frappe-ui'],
      },
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      port: 5173,
      ...(backendProxyUrl && {
        proxy: {
          '/api': { target: backendProxyUrl, changeOrigin: true, secure: false },
          '/socket.io': { target: backendProxyUrl, ws: true, changeOrigin: true, secure: false },
        },
      }),
    },
    optimizeDeps: {
      include: ['feather-icons', 'debug'],
      exclude: ['frappe-ui'],
    },
  }
})
