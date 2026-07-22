import { createApp } from 'vue'
import { FrappeUI } from 'frappe-ui'
import 'frappe-ui/style.css'
import './index.css'
import App from './App.vue'
import { router } from './router.js'
import { initializePlugins } from './plugins'

// Loads plugin frontends asynchronously; they register into the reactive
// pluginRegistry, so UI that depends on it (e.g. SettingsDialog) updates on
// its own once a plugin finishes loading - nothing here needs to await it.
initializePlugins()

const app = createApp(App)
app.use(router)
app.use(FrappeUI, { resources: false, call: false, socketio: false })

router.isReady().then(() => app.mount('#app'))
