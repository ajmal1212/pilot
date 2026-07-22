<template>
  <div class="mx-auto max-w-3xl">
    <!-- Header -->
    <div class="flex justify-between items-start gap-4 pt-4 pb-2">
      <div class="flex flex-col items-start">
        <div class="flex items-center gap-2.5">
          <h1 class="!font-semibold text-ink-gray-9 text-2xl sm:text-3xl tracking-tight">Explore Pilot Plugins</h1>
          <span class="inline-flex items-center gap-1 bg-surface-gray-2 px-2 py-0.5 rounded-full h-min text-ink-gray-6 text-p-xs shrink-0">
            <span class="size-3 lucide-plug"></span> {{ plugins.length }} {{ plugins.length === 1 ? 'Plugin' : 'Plugins' }}
          </span>
        </div>
        <p class="mt-2 max-w-lg text-ink-gray-6 text-p-base">
          Extend Pilot features by installing plugins directly from GitHub repositories
        </p>
      </div>

      <Button variant="solid" @click="showInstallDialog = true">
        <template #prefix><GithubMark class="size-4" /></template>
        Import plugin
      </Button>
    </div>

    <!-- Filters & Search Bar -->
    <div class="mt-6">
      <div class="flex sm:flex-row flex-col gap-2">
        <FormControl v-model="search" class="flex-1" type="text" placeholder="Search installed plugins">
          <template #prefix>
            <LucideSearch class="size-4 text-ink-gray-5" />
          </template>
        </FormControl>

        <Button variant="subtle" @click="showInstallDialog = true">
          <template #prefix><span class="size-4 lucide-plus" /></template>
          Add from GitHub
        </Button>
      </div>

      <!-- Category Pills -->
      <div class="flex flex-wrap gap-1.5 mt-3">
        <button
          v-for="pill in ['All', 'Active', 'Installed']"
          :key="pill"
          type="button"
          class="px-3 py-0.5 border rounded-full text-p-sm transition duration-150 ease-[var(--ease-out)] active:scale-[0.97]"
          :class="pill === selectedPill
            ? 'bg-surface-gray-3 border-outline-gray-2 text-ink-gray-9'
            : 'border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-1 hover:text-ink-gray-8'"
          @click="selectedPill = pill"
        >
          {{ pill }}
        </button>
      </div>
    </div>

    <!-- Loading / Error -->
    <div v-if="loading || error" class="flex flex-row justify-center items-center w-full h-[250px]">
      <LoadingText v-if="loading" class="mt-8" />
      <ErrorMessage v-else-if="error" :message="error" class="mt-8" />
    </div>

    <!-- Plugins List Section -->
    <template v-else>
      <section v-if="filteredPlugins.length" class="mt-10">
        <p class="font-medium text-ink-gray-9 text-base">Installed plugins</p>
        <div class="gap-x-6 gap-y-4 grid grid-cols-1 md:grid-cols-2 mt-3">
          <div
            v-for="plugin in filteredPlugins"
            :key="plugin.name"
            class="flex items-center gap-3 p-3 bg-surface-elevation-1 border border-outline-gray-2 rounded-xl transition duration-150 hover:border-outline-gray-3"
          >
            <!-- Logo Icon Box -->
            <div
              class="place-items-center grid rounded-[10px] size-10 overflow-hidden shrink-0 font-bold text-white text-base leading-none"
              :style="{ background: getLogoColor(plugin.name) }"
            >
              {{ plugin.name?.[0]?.toUpperCase() || 'P' }}
            </div>

            <!-- Plugin Metadata -->
            <div class="flex flex-1 justify-between items-center gap-2 py-1 min-w-0">
              <div class="min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="font-medium text-ink-gray-8 text-base truncate capitalize">{{ plugin.name }}</span>
                  <span class="text-ink-gray-5 text-p-xs shrink-0">v{{ plugin.version }}</span>
                </div>
                <div class="text-ink-gray-5 text-p-sm truncate">
                  {{ plugin.repo || 'Local plugin' }}
                  <template v-if="plugin.branch"> • {{ plugin.branch }}</template>
                </div>
              </div>

              <!-- Actions -->
              <div class="flex items-center gap-1 shrink-0">
                <Tooltip v-if="plugin.repo" text="Update Plugin">
                  <Button variant="ghost" size="sm" class="!px-2" :loading="updatingPlugin === plugin.name" @click="updatePlugin(plugin.name)">
                    <template #icon><span class="size-4 lucide-refresh-cw" /></template>
                  </Button>
                </Tooltip>
                <Tooltip text="Uninstall Plugin">
                  <Button variant="ghost" size="sm" class="!px-2 !text-ink-red-5 hover:!bg-surface-red-1" :loading="uninstallingPlugin === plugin.name" @click="confirmUninstall(plugin.name)">
                    <template #icon><span class="size-4 lucide-trash-2" /></template>
                  </Button>
                </Tooltip>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Empty State -->
      <div v-else class="mt-12 text-center py-12 border border-dashed border-outline-gray-2 rounded-xl bg-surface-elevation-1">
        <span class="size-8 text-ink-gray-4 lucide-plug mx-auto mb-2" />
        <p class="text-ink-gray-7 text-sm font-medium">No plugins found</p>
        <p class="text-ink-gray-5 text-xs mt-1">Import a plugin repository from GitHub to get started.</p>
        <Button variant="subtle" size="sm" class="mt-4" @click="showInstallDialog = true">
          <template #prefix><GithubMark class="size-3.5" /></template>
          Import plugin from GitHub
        </Button>
      </div>
    </template>
  </div>

  <!-- Install Plugin Dialog -->
  <Dialog v-model="showInstallDialog" :options="{ title: 'Import Plugin from GitHub', size: 'md' }">
    <template #body-content>
      <div class="flex flex-col gap-4">
        <p class="text-xs text-ink-gray-6">
          Enter the Git repository URL and branch for the plugin. Pilot will clone the repository, register its backend routes, and activate the UI.
        </p>

        <FormControl
          v-model="installForm.repo"
          label="Git Repository URL"
          type="text"
          placeholder="e.g. https://github.com/my-org/pilot-plugin-cloudflare"
          :autofocus="true"
        />

        <div class="grid grid-cols-2 gap-4">
          <FormControl
            v-model="installForm.branch"
            label="Branch"
            type="text"
            placeholder="main"
          />
          <FormControl
            v-model="installForm.name"
            label="Plugin Name (Optional)"
            type="text"
            placeholder="cloudflare"
          />
        </div>

        <p v-if="installError" class="text-xs text-red-600">{{ installError }}</p>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2 w-full">
        <Button variant="subtle" @click="showInstallDialog = false">Cancel</Button>
        <Button variant="solid" :loading="installing" @click="doInstall">Import Plugin</Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dialog, ErrorMessage, FormControl, LoadingText, Tooltip, toast } from 'frappe-ui'
import LucideSearch from '~icons/lucide/search'
import GithubMark from '@/components/icons/GithubMark.vue'
import { pluginsApi } from '@/api/plugins'
import { apiErrorMessage } from '@/api/client'
import { openTaskDetailPage } from '@/utils/taskRoute'
import { logoColor } from '@/composables/apps/useMarketplace'

const router = useRouter()

const loading = ref(true)
const error = ref(null)
const plugins = ref([])
const search = ref('')
const selectedPill = ref('All')

const showInstallDialog = ref(false)
const installing = ref(false)
const installError = ref('')
const installForm = ref({
  repo: '',
  branch: 'main',
  name: '',
})

const updatingPlugin = ref(null)
const uninstallingPlugin = ref(null)

const filteredPlugins = computed(() => {
  return plugins.value.filter((p) => {
    const matchesSearch = !search.value || p.name.toLowerCase().includes(search.value.toLowerCase()) || (p.repo && p.repo.toLowerCase().includes(search.value.toLowerCase()))
    return matchesSearch
  })
})

function getLogoColor(name) {
  return logoColor(name)
}

async function loadPlugins() {
  loading.value = true
  error.value = null
  try {
    const res = await pluginsApi.list()
    if (res.error) {
      error.value = apiErrorMessage(res)
    } else {
      plugins.value = res.plugins || []
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function doInstall() {
  installError.value = ''
  if (!installForm.value.repo || !installForm.value.repo.trim()) {
    installError.value = 'Please enter a valid Git Repository URL.'
    return
  }

  installing.value = true
  try {
    const res = await pluginsApi.install(installForm.value)
    if (res.error) {
      installError.value = apiErrorMessage(res, 'Failed to queue plugin installation.')
    } else {
      toast.success('Plugin installation task started!')
      showInstallDialog.value = false
      installForm.value = { repo: '', branch: 'main', name: '' }
      if (res.task_id) {
        openTaskDetailPage(router, res.task_id)
      }
      await loadPlugins()
    }
  } catch (err) {
    installError.value = err.message
  } finally {
    installing.value = false
  }
}

async function updatePlugin(name) {
  updatingPlugin.value = name
  try {
    const res = await pluginsApi.update(name)
    if (res.error) {
      toast.error(apiErrorMessage(res, 'Failed to update plugin.'))
    } else {
      toast.success(`Plugin ${name} updated successfully!`)
      await loadPlugins()
    }
  } catch (err) {
    toast.error(err.message)
  } finally {
    updatingPlugin.value = null
  }
}

async function confirmUninstall(name) {
  if (!confirm(`Are you sure you want to uninstall plugin "${name}"? This will delete the plugin files.`)) {
    return
  }
  uninstallingPlugin.value = name
  try {
    const res = await pluginsApi.uninstall(name)
    if (res.error) {
      toast.error(apiErrorMessage(res, 'Failed to uninstall plugin.'))
    } else {
      toast.success(`Plugin ${name} uninstalled successfully.`)
      await loadPlugins()
    }
  } catch (err) {
    toast.error(err.message)
  } finally {
    uninstallingPlugin.value = null
  }
}

onMounted(loadPlugins)
</script>
