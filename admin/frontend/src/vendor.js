// Built to a stable, unhashed URL (see vite.config.js) so plugin bundles can
// resolve `vue`, `vue-router`, and `frappe-ui` here via the import map in
// index.html and share the exact same module instances as the core app.
// vue-router is included because frappe-ui itself depends on it internally
// (router-aware components) - without sharing it too, frappe-ui's bundled
// copy ends up with its own router injection keys that never match the
// ones core's actual router installs, and any component that calls
// useRoute()/useRouter() breaks.
export * from 'vue'
export * from 'vue-router'
export * from 'frappe-ui'
