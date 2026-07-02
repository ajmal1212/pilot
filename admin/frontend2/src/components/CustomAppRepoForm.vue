<template>
  <div class="flex flex-col gap-4">
    <TabButtons type="underline" :model-value="tab" :options="tabOptions" @update:model-value="switchTab" />

    <template v-if="tab === 'public'">
      <div>
        <p class="mb-1.5 font-medium text-ink-gray-6 text-p-sm">GitHub URL</p>
        <div class="flex gap-2">
          <TextInput v-model="repo" placeholder="https://github.com/frappe/crm" class="flex-1" />
          <Combobox v-if="fetched" v-model="branch" :options="branchOptions" :loading="fetching"
            placeholder="Branch" class="w-40" @update:selectedOption="onBranchSelect" />
          <Button v-else variant="subtle" :loading="fetching" :disabled="!repo.trim()" @click="fetchBranches">
            Fetch Branches
          </Button>
        </div>
      </div>
    </template>

    <template v-else>
      <div v-if="!gitStatus" class="py-4 text-ink-gray-4 text-sm text-center">Loading…</div>
      <Alert v-else-if="!gitConnected" theme="yellow" title="No GitHub account connected" :dismissible="false">
        <template #description>
          <p class="text-ink-gray-6 text-p-sm">Connect a personal access token from Settings → GitHub to browse
            your repositories.</p>
        </template>
      </Alert>
      <template v-else>
        <div>
          <p class="mb-1.5 font-medium text-ink-gray-6 text-p-sm">Choose GitHub User / Organization</p>
          <div class="flex items-center gap-2 px-3 py-2 border rounded-lg border-outline-gray-2">
            <span class="place-items-center grid bg-surface-gray-3 rounded-full size-6 text-ink-gray-7 text-xs shrink-0">
              {{ gitStatus.username?.[0]?.toUpperCase() }}
            </span>
            <span class="text-ink-gray-8 text-sm">{{ gitStatus.username }}</span>
          </div>
        </div>

        <div>
          <p class="mb-1.5 font-medium text-ink-gray-6 text-p-sm">Choose GitHub Repository</p>
          <Combobox v-model="repo" :options="repoOptions" :loading="reposLoading" placeholder="Select a repository…"
            emptyText="No repositories found." @update:selectedOption="onRepoSelect" />
        </div>
      </template>
    </template>

    <p v-if="resolving" class="text-ink-gray-5 text-sm">Checking repository…</p>
    <p v-else-if="foundName" class="flex items-center gap-1.5 text-ink-green-4 text-sm">
      <span class="lucide-circle-check size-4"></span>
      Found {{ foundTitle }} ({{ foundName }})
    </p>

    <Alert v-if="exists" theme="yellow" :dismissible="false">
      <template #description>
        <p class="text-ink-gray-6 text-p-sm">
          App <strong>{{ foundName }}</strong> already exists on this Bench. Clicking on Update App will change
          app source to the selected one.
        </p>
      </template>
    </Alert>

    <ErrorMessage v-if="error" :message="error" />

    <Button variant="solid" size="lg" class="w-full" :disabled="!canSubmit" :loading="resolving || submitting"
      @click="submit">
      {{ exists ? 'Update App' : 'Add App' }}
    </Button>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Alert, Button, Combobox, ErrorMessage, TabButtons, TextInput } from 'frappe-ui'
import { gitApi } from '@/api/git'
import { useAppRegistry } from '@/composables/useAppRegistry'

const props = defineProps({
  existingApps: { type: Array, default: () => [] },
  submitting: { type: Boolean, default: false },
})
const emit = defineEmits(['submit'])

const { titleMap, load: loadRegistry } = useAppRegistry()

const tab = ref('public')
const repo = ref('')
const branch = ref('')
const error = ref('')

const tabOptions = [
  { label: 'Public GitHub App', value: 'public' },
  { label: 'Your GitHub App', value: 'private' },
]

// Public tab — manual URL + fetched branch list
const fetched = ref(false)
const fetching = ref(false)
const branches = ref([])
const branchOptions = computed(() => branches.value.map((b) => ({ label: b, value: b })))

// Private tab — connected account + repo browser
const gitStatus = ref(null)
const gitConnected = computed(() => Boolean(gitStatus.value?.connected && gitStatus.value?.is_token_valid))
const repos = ref([])
const reposLoading = ref(false)
const repoByCloneUrl = computed(() => new Map(repos.value.map((r) => [r.clone_url, r])))
const repoOptions = computed(() => repos.value.map((r) => ({ label: r.full_name, value: r.clone_url })))

// Resolved app identity, shared by both tabs
const resolving = ref(false)
const foundName = ref('')
const foundTitle = computed(() => titleMap.value[foundName.value] || foundName.value)
const exists = computed(() => Boolean(foundName.value) && props.existingApps.includes(foundName.value))
const canSubmit = computed(() => Boolean(repo.value.trim()) && !resolving.value)

async function fetchBranches() {
  const url = repo.value.trim()
  if (!url) return
  fetching.value = true
  error.value = ''
  try {
    const d = await gitApi.branches(url)
    if (d.ok) {
      branches.value = d.branches
      branch.value = d.branches[0] || ''
      fetched.value = true
      resolveApp()
    } else {
      error.value = d.error
    }
  } catch (e) {
    error.value = e.message
  } finally {
    fetching.value = false
  }
}

function onBranchSelect(option) {
  if (option) resolveApp()
}

async function loadGitStatus() {
  try {
    gitStatus.value = await gitApi.status()
    if (gitConnected.value) loadRepos()
  } catch (e) {
    error.value = e.message
  }
}

async function loadRepos() {
  reposLoading.value = true
  try {
    const d = await gitApi.repos()
    if (d.ok) repos.value = d.repos
    else error.value = d.error
  } catch (e) {
    error.value = e.message
  } finally {
    reposLoading.value = false
  }
}

function onRepoSelect(option) {
  if (!option) return
  const found = repoByCloneUrl.value.get(option.value)
  if (!found) return
  branch.value = found.default_branch || ''
  resolveApp()
}

async function resolveApp() {
  const url = repo.value.trim()
  if (!url) return
  resolving.value = true
  foundName.value = ''
  error.value = ''
  try {
    const d = await gitApi.resolve(url, branch.value.trim())
    if (d.ok) foundName.value = d.name
  } catch {
    // Resolution is a best-effort preview — the install itself resolves the app name again.
  } finally {
    resolving.value = false
  }
}

function resetPublic() {
  fetched.value = false
  branches.value = []
  foundName.value = ''
}

watch(repo, resetPublic)

function switchTab(next) {
  tab.value = next
  repo.value = ''
  branch.value = ''
  error.value = ''
  resetPublic()
  if (next === 'private' && !gitStatus.value) loadGitStatus()
}

function submit() {
  if (!canSubmit.value) return
  emit('submit', { name: foundName.value, repo: repo.value.trim(), branch: branch.value.trim(), exists: exists.value })
}

onMounted(loadRegistry)
</script>
