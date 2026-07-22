import { ref } from 'vue'

class PluginRegistry {
  constructor() {
    this.settingsSections = ref([])
    this.siteSettingsComponents = ref([])
  }

  registerSettingsSection(section) {
    /**
     * section: { id: string, label: string, icon: string, component: Component }
     */
    const index = this.settingsSections.value.findIndex((s) => s.id === section.id)
    if (index >= 0) {
      this.settingsSections.value[index] = section
    } else {
      this.settingsSections.value.push(section)
    }
  }

  registerSiteSettingsComponent(card) {
    /**
     * card: { id: string, component: Component }
     */
    const index = this.siteSettingsComponents.value.findIndex((c) => c.id === card.id)
    if (index >= 0) {
      this.siteSettingsComponents.value[index] = card
    } else {
      this.siteSettingsComponents.value.push(card)
    }
  }

  getSettingsSections() {
    return this.settingsSections.value
  }

  getSiteSettingsComponents() {
    return this.siteSettingsComponents.value
  }
}

export const pluginRegistry = new PluginRegistry()
