import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import frappeuiPlugin from 'frappe-ui/vite'

// A plugin's frontend is its own independent build (see
// docs/plugin-frontend.md at the repo root): vue/vue-router/frappe-ui stay
// external, resolved at runtime through the Admin UI's import map, so this
// plugin shares the exact same instances core uses instead of bundling its
// own copies.
export default defineConfig({
  plugins: [
    frappeuiPlugin({
      lucideIcons: true,
      frappeProxy: false,
      jinjaBootData: false,
      buildConfig: false,
    }),
    vue(),
  ],
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
  build: {
    outDir: 'dist',
    lib: {
      entry: path.resolve(__dirname, 'src/index.js'),
      formats: ['es'],
      fileName: () => 'index.js',
    },
    rollupOptions: {
      external: ['vue', 'vue-router', 'frappe-ui'],
      output: {
        inlineDynamicImports: true,
        assetFileNames: 'index.[ext]',
      },
    },
  },
})
