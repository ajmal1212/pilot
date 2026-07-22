import { watch } from 'vue'
import { pluginsApi } from '@/api/plugins'
import { pluginRegistry } from '@/plugins/registry'
import { useSession } from '@/composables/auth/useSession'

/**
 * Loads every installed plugin's frontend bundle at runtime and lets it
 * register into `pluginRegistry`. A plugin ships `frontend/dist/index.js`
 * (an ES module exporting `init(registry)`) and an optional
 * `frontend/dist/index.css`; both are served by the backend at
 * `/api/v1/plugins/<name>/assets/...`. `index.js` resolves `vue`/`frappe-ui`
 * through the import map in index.html, so it shares this app's exact Vue
 * instance instead of shipping its own.
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
    loadPluginStylesheet(name)
    const mod = await import(/* @vite-ignore */ `/api/v1/plugins/${name}/assets/index.js`)
    await mod.init?.(pluginRegistry)
  } catch (e) {
    console.error(`Failed to load frontend for plugin "${name}"`, e)
  }
}

function loadPluginStylesheet(name) {
  const id = `plugin-style-${name}`
  if (document.getElementById(id)) return
  const link = document.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = `/api/v1/plugins/${name}/assets/index.css`
  document.head.appendChild(link)
}
