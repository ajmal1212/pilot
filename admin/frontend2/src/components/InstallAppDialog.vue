<template>
  <Dialog v-model="open" :options="dialogOptions">
    <template #body-content>
      <template v-if="mode === 'repo'">
        <CustomAppRepoForm :existing-apps="existingApps" :submitting="installing" @submit="onCustomRepoChosen" />
        <ErrorMessage v-if="error" :message="error" class="mt-3" />
      </template>

      <template v-else>
        <p v-if="presetSite" class="text-ink-gray-7 text-sm">
          Install <strong>{{ appLabel }}</strong> on <strong>{{ presetSite.name }}</strong>?
          <span v-if="presetInstalled" class="block mt-1 text-ink-gray-5">Already installed on this site.</span>
        </p>

        <div v-else class="gap-2 grid px-2 max-h-96 overflow-y-auto">
          <button type="button" class="flex items-center gap-3 p-3 border rounded-lg text-left transition-colors"
            :class="rowClass('all')" :disabled="!installableSites.length" @click="selection = 'all'">
            <span class="place-items-center grid bg-surface-gray-2 rounded-md size-8 shrink-0">
              <span class="lucide-layout-grid size-4 text-ink-gray-6" />
            </span>
            <div class="flex-1 min-w-0">
              <p class="font-medium text-ink-gray-8 text-sm">All sites</p>
              <p class="text-ink-gray-5 text-p-sm truncate">
                Installs on {{ installableSites.length }} site{{ installableSites.length === 1 ? '' : 's' }}
              </p>
            </div>
          </button>

          <button v-for="s in sites" :key="s.name" type="button"
            class="flex items-center gap-3 p-3 border rounded-lg min-w-0 text-left transition-colors"
            :class="isInstalled(s) ? 'border-outline-gray-2 opacity-60 cursor-not-allowed' : rowClass(s.name)"
            :disabled="isInstalled(s)" @click="selection = s.name">
            <span class="place-items-center grid bg-surface-gray-2 rounded-md size-8 shrink-0">
              <span class="size-4 text-ink-gray-6 lucide-globe" />
            </span>
            <div class="flex-1 min-w-0">
              <p class="font-medium text-ink-gray-8 text-sm truncate">{{ s.name }}</p>
              <p class="text-ink-gray-5 text-p-sm truncate">
                {{ s.name }} · {{ isInstalled(s) ? 'already installed' : siteVersion(s) || 'latest' }}
              </p>
            </div>
          </button>

          <p v-if="!sites.length" class="py-6 text-ink-gray-5 text-sm text-center">
            No sites available on this bench.
          </p>
        </div>

        <ErrorMessage v-if="error" :message="error" class="mt-3" />

        <div class="flex justify-end gap-2 mt-5">
          <Button v-if="custom" variant="ghost" class="mr-auto" @click="mode = 'repo'">← Back</Button>
          <Button variant="subtle" @click="open = false">Cancel</Button>
          <Button variant="solid" :disabled="!selection || presetInstalled" :loading="installing" @click="confirmInstall">
            Install
          </Button>
        </div>
      </template>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dialog, ErrorMessage } from 'frappe-ui'
import CustomAppRepoForm from '@/components/CustomAppRepoForm.vue'
import { appsApi } from '@/api/apps'
import { sitesApi } from '@/api/sites'
import { openTaskDetailPage } from '@/utils/taskRoute'

const props = defineProps({
  app: { type: Object, default: null },
  sites: { type: Array, default: () => [] },
  siteName: { type: String, default: '' },
  custom: { type: Boolean, default: false },
  existingApps: { type: Array, default: () => [] },
})
const open = defineModel('open')
const router = useRouter()

const mode = ref('sites') // 'repo' (custom app entry) | 'sites' (target picker)
const selection = ref(null)
const installing = ref(false)
const error = ref('')
const customRepo = ref('')
const customBranch = ref('')

const dialogOptions = computed(() => ({
  title: mode.value === 'repo' ? 'Add app from GitHub' : `Install ${appLabel.value}`,
  size: mode.value === 'repo' ? 'lg' : 'md',
}))
const appLabel = computed(() => props.app?.title || customRepo.value || 'App')

const presetSite = computed(() => props.sites.find((s) => s.name === props.siteName) || null)
const presetInstalled = computed(() => Boolean(presetSite.value && isInstalled(presetSite.value)))

watch(open, (isOpen) => {
  if (!isOpen) return
  selection.value = props.siteName || null
  error.value = ''
  mode.value = props.custom ? 'repo' : 'sites'
})

async function onCustomRepoChosen({ name, repo, branch, exists }) {
  customRepo.value = repo
  customBranch.value = branch
  error.value = ''

  if (!exists) {
    mode.value = 'sites'
    return
  }

  installing.value = true
  try {
    const result = await appsApi.updateSource(name, { repo, branch })
    if (!result.ok) throw new Error(result.error || `Could not update ${name}.`)
    open.value = false
    openTaskDetailPage(router, result.task_id)
  } catch (caught) {
    error.value = caught.message || 'Could not start update.'
  } finally {
    installing.value = false
  }
}

const installableSites = computed(() => props.sites.filter((s) => !isInstalled(s)))

function isInstalled(site) {
  return Boolean(props.app && site.installed_apps?.includes(props.app.name))
}

function siteVersion(site) {
  const match = /^version-(\d+)/.exec(site.site_config?.frappe_branch || '')
  return match ? `Version ${match[1]}` : ''
}

function rowClass(value) {
  return selection.value === value
    ? 'border-outline-gray-4 ring-1 ring-outline-gray-4 bg-surface-gray-1'
    : 'border-outline-gray-2 hover:bg-surface-gray-1'
}

async function startInstall(site) {
  const payload = props.custom
    ? { repo: customRepo.value, branch: customBranch.value }
    : { app: props.app.name, repo: props.app.repo, branch: props.app.branch || '' }
  const result = await sitesApi.apps.getAndInstall(site.name, payload)
  if (!result.ok) throw new Error(result.error || `Could not install on ${site.name}.`)
  return result.task_id
}

async function installOnSite(name) {
  const site = props.sites.find((s) => s.name === name)
  if (!site) return
  const taskId = await startInstall(site)
  open.value = false
  openTaskDetailPage(router, taskId)
}

async function installOnAllSites() {
  const targets = installableSites.value
  if (!targets.length) return
  await Promise.all(targets.map((site) => startInstall(site)))
  open.value = false
  router.push({ name: 'Tasks' })
}

async function confirmInstall() {
  if (!selection.value || installing.value) return
  error.value = ''
  installing.value = true
  try {
    if (selection.value === 'all') await installOnAllSites()
    else await installOnSite(selection.value)
  } catch (caught) {
    error.value = caught.message || 'Could not start install.'
  } finally {
    installing.value = false
  }
}
</script>
