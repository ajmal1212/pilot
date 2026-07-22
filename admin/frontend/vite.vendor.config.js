import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import frappeuiPlugin from 'frappe-ui/vite'

// Builds src/vendor.js (a flat re-export of vue + frappe-ui) as a
// self-contained ES module at a stable URL, independent of the main app
// build in vite.config.js. Kept as its own `vite build` invocation (see
// package.json's "build" script) rather than a second entry in the main
// config: mixing a real bundled entry with other entries that externalize
// the same dependencies confused Rolldown's tree-shaking (some internal
// Vue helpers ended up dropped despite being reachable). Two independent,
// single-purpose builds sidestep that entirely.
export default defineConfig({
  // Vite's main app build auto-replaces process.env.NODE_ENV; this
  // separate build needs the same replacement for Vue's own legacy
  // Node-style env checks (they run as real browser code here).
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
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
    outDir: '../backend/static/dist/plugin-runtime',
    emptyOutDir: false,
    minify: true,
    lib: {
      entry: path.resolve(__dirname, 'src/vendor.js'),
      formats: ['es'],
      fileName: () => 'vendor.js',
    },
    rollupOptions: {
      // One file, no relative-chunk fan-out: everything a plugin might
      // import from 'vue'/'frappe-ui' has to live in this one entry, since
      // it's the only URL the import map points at.
      output: { inlineDynamicImports: true },
    },
  },
})
