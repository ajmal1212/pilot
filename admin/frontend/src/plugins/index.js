import { watch } from 'vue'
import { pluginsApi } from '@/api/plugins'
import { pluginRegistry } from '@/plugins/registry'
import { useSession } from '@/composables/auth/useSession'

/**
 * Loads every installed plugin's frontend bundle at runtime and lets it
 * register into `pluginRegistry`. A plugin ships `frontend/dist/index.js`
 * (an ES module exporting `init(registry)`), served by the backend at
 * `/api/v1/plugins/<name>/assets/index.js`. It resolves `vue`/`vue-router`/
 * `frappe-ui` through the import map in index.html, so it shares this app's
 * exact instances instead of shipping its own.
 *
 * Deliberately does NOT auto-load a plugin CSS file - see
 * docs/plugin-frontend.md. A plugin's own Tailwind build re-declares
 * globally-scoped utility classes (e.g. `.hidden`) that core also defines;
 * loading it after core's stylesheet flips which one wins the cascade for
 * the *entire page*, not just the plugin's own markup. A plugin should
 * render with frappe-ui components and Tailwind classes core's build
 * already includes - both share the same frappe-ui/tailwind preset, so
 * that's rarely a real limitation in practice.
 *
 * `/api/v1/plugins` requires an authenticated session, which doesn't exist
 * yet when this is called at app boot, so it waits for `session.authenticated`
 * (already-restored session or a fresh login) rather than loading once and
 * giving up on the pre-login 401. Failures are isolated per plugin, so a
 * broken plugin bundle never blocks or breaks the rest of Pilot's UI.
 */
export function initializePlugins() {
  const { session } = useSession()
  const stopWatching = watch(
    () => session.authenticated,
    (authenticated) => {
      if (!authenticated) return
      stopWatching()
      loadAllPlugins()
    },
    { immediate: true },
  )
}

async function loadAllPlugins() {
  let plugins
  try {
    const res = await pluginsApi.list()
    plugins = res.plugins || []
  } catch (e) {
    console.error('Failed to list plugins', e)
    return
  }

  for (const plugin of plugins) {
    if (!plugin.has_frontend) continue
    await loadPluginFrontend(plugin.name)
  }
}

async function loadPluginFrontend(name) {
  try {
    const mod = await import(/* @vite-ignore */ `/api/v1/plugins/${name}/assets/index.js`)
    await mod.init?.(pluginRegistry)
  } catch (e) {
    console.error(`Failed to load frontend for plugin "${name}"`, e)
  }
}
