<template>
  <div class="space-y-9 mt-5">
    <SettingsGeneral :site-name="siteName" />
    <SettingsDomains :site-name="siteName" />
    <component
      :is="card.component"
      v-for="card in pluginSiteSettingsComponents"
      :key="card.id"
      :site-name="siteName"
    />
    <SettingsActions :site-name="siteName" />
    <SettingsDanger :site-name="siteName" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SettingsGeneral from './settings/General.vue'
import SettingsDomains from './settings/Domains.vue'
import SettingsActions from './settings/Actions.vue'
import SettingsDanger from './settings/Danger.vue'
import { pluginRegistry } from '@/plugins/registry'

defineProps({ siteName: { type: String, required: true } })

const pluginSiteSettingsComponents = computed(() => pluginRegistry.getSiteSettingsComponents())
</script>
