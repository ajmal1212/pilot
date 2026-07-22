import CloudflareSettings from '@/components/settings/CloudflareSettings.vue'
import SettingsTunnel from '@/components/sites/settings/Tunnel.vue'
import { pluginRegistry } from '@/plugins/registry'

export function initCloudflarePlugin() {
  pluginRegistry.registerSettingsSection({
    id: 'cloudflare',
    label: 'Cloudflare',
    icon: 'lucide-cloud',
    component: CloudflareSettings,
  })

  pluginRegistry.registerSiteSettingsComponent({
    id: 'cloudflare-tunnel',
    component: SettingsTunnel,
  })
}
