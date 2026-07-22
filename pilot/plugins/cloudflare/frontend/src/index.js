import './style.css'
import CloudflareSettings from './CloudflareSettings.vue'
import Tunnel from './Tunnel.vue'

export function init(registry) {
  registry.registerSettingsSection({
    id: 'cloudflare',
    label: 'Cloudflare',
    icon: 'lucide-cloud',
    component: CloudflareSettings,
  })

  registry.registerSiteSettingsComponent({
    id: 'cloudflare-tunnel',
    component: Tunnel,
  })
}
