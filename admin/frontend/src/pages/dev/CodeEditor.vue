<template>
  <!-- App selector on the right of the header -->
  <Teleport defer to="#header-actions">
    <div class="flex items-center gap-2">
      <!-- Action buttons -->
      <div class="flex items-center gap-2" v-if="selectedApp">
        <Button variant="outline" size="sm" @click="showTerminal = !showTerminal">
          <template #prefix><span class="size-4 lucide-terminal" /></template>
          Terminal
        </Button>
        <template v-if="activeFile">
          <span v-if="isModified" class="size-2 rounded-full bg-amber-500 shrink-0" title="Modified" />
          <Button variant="solid" size="sm" :loading="saving" :disabled="!isModified" @click="saveCurrentFile">
            <template #prefix><span class="size-4 lucide-save" /></template>
            Save
          </Button>
        </template>
      </div>

      <FormControl type="select" v-model="selectedApp" :options="appOptions"
        class="w-28 sm:w-44 max-w-[140px] sm:max-w-[180px]" />
    </div>
  </Teleport>

  <!-- Workspace Main Split View -->
  <div class="flex bg-surface-base overflow-hidden h-[calc(100vh-53px)] -m-4 sm:-m-6">
    <!-- Left Sidebar: File Tree Explorer -->
    <div class="w-64 border-r border-outline-gray-2 bg-surface-gray-1 flex flex-col shrink-0 overflow-y-auto hover-scrollbar">
      <div class="p-3 border-b border-outline-gray-2 bg-surface-base flex items-center justify-between">
        <p class="text-xs font-semibold text-ink-gray-5 uppercase tracking-wider">Explorer</p>
        <span v-if="activeFile" class="text-[10px] font-mono text-ink-gray-4 truncate max-w-[120px]">{{ activeFile.name }}</span>
      </div>

      <div v-if="!selectedApp" class="p-4 text-center text-xs text-ink-gray-4">
        Choose an app to browse files.
      </div>
      <div v-else-if="loadingTree" class="p-4 text-center text-xs text-ink-gray-4">
        Loading file tree...
      </div>
      <div v-else-if="!fileTree.length" class="p-4 text-center text-xs text-ink-gray-4">
        No files found in app.
      </div>
      <div v-else class="p-2 space-y-0.5">
        <!-- Recursive File Tree Node component -->
        <FileTreeNode 
          v-for="node in fileTree" 
          :key="node.path" 
          :node="node" 
          :active-path="activeFile?.path"
          @select-file="selectFile" 
        />
      </div>
    </div>

    <!-- Right Panel: Editor Workspace -->
    <div class="flex-1 flex flex-col overflow-hidden bg-surface-base relative">
      <div v-if="!selectedApp" class="flex flex-col items-center justify-center h-full gap-2 text-ink-gray-4">
        <span class="size-8 lucide-folder-open text-ink-gray-3" />
        <p class="text-sm">Select an app to start exploring the workspace.</p>
      </div>
      <div v-else class="flex-1 flex flex-col min-h-0 overflow-hidden">
        <!-- Editor View Container (Visible when file is selected) -->
        <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
          <div v-if="!activeFile" class="flex flex-col items-center justify-center h-full gap-2 text-ink-gray-4">
            <span class="size-8 lucide-code-2 text-ink-gray-3" />
            <p class="text-sm">Select a file from the explorer to open it.</p>
          </div>
          <div v-else-if="loadingFile" class="flex items-center justify-center h-full text-ink-gray-4">
            Loading file content...
          </div>
          <div v-else class="flex-1 flex flex-col min-h-0 overflow-hidden">
            <!-- Editor Component -->
            <div class="flex-1 overflow-hidden relative">
              <Codemirror
                v-model="editorContent"
                :extensions="extensions"
                :style="{ height: '100%' }"
                @ready="onEditorReady"
              />
            </div>
            <!-- Status Bar -->
            <div class="h-6 px-4 bg-surface-gray-1 border-t border-outline-gray-2 flex items-center justify-between text-xs text-ink-gray-5 shrink-0">
              <div class="truncate max-w-[200px] sm:max-w-md font-mono text-[11px]">{{ activeFile.path }} ({{ fileType }})</div>
              <div class="tabular-nums">Lines: {{ lineCount }}</div>
            </div>
          </div>
        </div>

        <!-- Terminal Pane Drawer -->
        <div v-if="showTerminal" class="h-64 border-t border-outline-gray-2 flex flex-col bg-[#0f172a] shrink-0">
          <!-- Terminal Header -->
          <div class="flex items-center justify-between px-3 py-1.5 bg-[#1e293b] border-b border-outline-gray-2 text-xs text-slate-300">
            <div class="flex items-center gap-1.5">
              <span class="size-3.5 lucide-terminal" />
              <span class="font-medium">Terminal Console</span>
            </div>
            <button @click="showTerminal = false" class="hover:text-white transition-colors">
              <span class="size-3.5 lucide-x" />
            </button>
          </div>
          <!-- Terminal Body -->
          <div class="flex-1 min-h-0">
            <WebTerminal />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { Button, FormControl, toast } from 'frappe-ui'
import { workspaceApi } from '@/api/workspace'
import FileTreeNode from './FileTreeNode.vue'
import WebTerminal from '@/components/dev/WebTerminal.vue'

// CodeMirror imports
import { Codemirror } from 'vue-codemirror'
import { autocompletion } from '@codemirror/autocomplete'
import { history, historyKeymap, defaultKeymap, indentWithTab } from '@codemirror/commands'
import { keymap, EditorView, lineNumbers, drawSelection, highlightActiveLine, highlightActiveLineGutter } from '@codemirror/view'
import { Prec } from '@codemirror/state'
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { tags } from '@lezer/highlight'

// Language extensions installed via npm
import { python } from '@codemirror/lang-python'
import { javascript } from '@codemirror/lang-javascript'
import { html } from '@codemirror/lang-html'
import { css } from '@codemirror/lang-css'

// ── State ─────────────────────────────────────────────────────────────────────

const apps = ref([])
const selectedApp = ref('')
const showTerminal = ref(false)
const appOptions = computed(() => [
  { label: 'Select App', value: '' },
  ...apps.value.map((a) => ({ label: a, value: a })),
])
const fileTree = ref([])
const loadingTree = ref(false)
const activeFile = ref(null)
const loadingFile = ref(false)
const editorContent = ref('')
const originalContent = ref('')
const saving = ref(false)

const view = shallowRef(null)

const isModified = computed(() => {
  return activeFile.value && editorContent.value !== originalContent.value
})

const fileType = computed(() => {
  if (!activeFile.value) return ''
  const ext = activeFile.value.path.split('.').pop().toLowerCase()
  const mappings = {
    py: 'Python',
    js: 'JavaScript',
    vue: 'Vue Component',
    json: 'JSON Configuration',
    css: 'CSS Stylesheet',
    html: 'HTML Document',
    md: 'Markdown',
    sh: 'Shell Script',
  }
  return mappings[ext] || 'Plain Text'
})

const lineCount = computed(() => {
  return editorContent.value.split('\n').length
})

// ── CodeMirror Theme & Extensions ─────────────────────────────────────────────

const editorTheme = EditorView.theme({
  '&': {
    height: '100%',
    fontSize: '13px',
    color: 'var(--ink-gray-8, #1e293b)',
    backgroundColor: 'var(--surface-base, white)',
  },
  '&.cm-focused': { outline: 'none' },
  '.cm-scroller': {
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
    lineHeight: '22px',
    overflow: 'auto',
  },
  '.cm-content': {
    caretColor: 'var(--ink-gray-8, #1e293b)',
    padding: '10px 0',
  },
  '.cm-line': { padding: '0 16px' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--ink-gray-8, #1e293b)' },
  '.cm-gutters': {
    backgroundColor: 'var(--surface-gray-1, #f8fafc)',
    borderRight: '1px solid var(--outline-gray-2, #e8eaed)',
    color: 'var(--ink-gray-4, #9aa0a6)',
  },
  '.cm-activeLine': {
    backgroundColor: 'color-mix(in srgb, var(--ink-gray-9, #0f0f0f) 3%, transparent)',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'color-mix(in srgb, var(--ink-gray-9, #0f0f0f) 3%, transparent)',
    color: 'var(--ink-gray-6, #5f6368)',
  },
  '.cm-selectionBackground': { backgroundColor: 'rgba(99, 102, 241, 0.15)' },
  '&.cm-focused .cm-selectionBackground': { backgroundColor: 'rgba(99, 102, 241, 0.22)' },
})

const sqlHighlightStyle = HighlightStyle.define([
  { tag: [tags.keyword, tags.standard(tags.name)], color: 'var(--ink-indigo-6, #4f46e5)' },
  { tag: [tags.string, tags.special(tags.string)], color: 'var(--ink-green-6, #16a34a)' },
  { tag: [tags.lineComment, tags.blockComment], color: 'var(--ink-gray-5, #64748b)', fontStyle: 'italic' },
  { tag: [tags.number, tags.bool, tags.null], color: 'var(--ink-amber-6, #d97706)' },
  { tag: tags.typeName, color: 'var(--ink-amber-6, #d97706)' },
  { tag: tags.special(tags.name), color: 'var(--ink-violet-6, #7c3aed)' },
  { tag: tags.name, color: 'var(--ink-gray-8, #1e293b)' },
  { tag: [tags.operator, tags.punctuation, tags.paren, tags.brace, tags.squareBracket], color: 'var(--ink-gray-6, #5f6368)' },
])

const saveKeymap = Prec.highest(keymap.of([{
  key: 'Mod-s',
  run: () => {
    if (isModified.value) saveCurrentFile()
    return true
  },
}]))

// Dynamic language parser selection based on file extension
const getLanguageExtension = () => {
  if (!activeFile.value) return []
  const ext = activeFile.value.path.split('.').pop().toLowerCase()
  if (ext === 'py') return [python()]
  if (['js', 'jsx', 'ts', 'tsx', 'vue'].includes(ext)) return [javascript({ jsx: true, typescript: true })]
  if (ext === 'html') return [html()]
  if (ext === 'css') return [css()]
  return []
}

const extensions = computed(() => [
  editorTheme,
  Prec.highest(syntaxHighlighting(sqlHighlightStyle)),
  lineNumbers(),
  drawSelection(),
  highlightActiveLine(),
  highlightActiveLineGutter(),
  history(),
  keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
  autocompletion({ activateOnTyping: true }),
  saveKeymap,
  ...getLanguageExtension(),
])

// ── API Operations ────────────────────────────────────────────────────────────

async function loadApps() {
  try {
    const res = await workspaceApi.apps()
    apps.value = res.apps || []
  } catch (e) {
    toast.error('Could not load apps list.')
  }
}

async function loadTree() {
  if (!selectedApp.value) {
    fileTree.value = []
    return
  }
  loadingTree.value = true
  try {
    const res = await workspaceApi.tree(selectedApp.value)
    fileTree.value = res.tree || []
  } catch (e) {
    toast.error('Could not load file tree.')
  } finally {
    loadingTree.value = false
  }
}

async function selectFile(node) {
  if (node.is_dir) return
  loadingFile.value = true
  activeFile.value = node
  try {
    const res = await workspaceApi.getFile(selectedApp.value, node.path)
    editorContent.value = res.content
    originalContent.value = res.content
  } catch (e) {
    toast.error(`Could not read file: ${e.message || e}`)
    activeFile.value = null
  } finally {
    loadingFile.value = false
  }
}

async function saveCurrentFile() {
  if (!activeFile.value || saving.value) return
  saving.value = true
  try {
    await workspaceApi.saveFile(selectedApp.value, activeFile.value.path, editorContent.value)
    originalContent.value = editorContent.value
    toast.success(`Successfully saved ${activeFile.value.name}`)
  } catch (e) {
    toast.error(`Could not save file: ${e.message || e}`)
  } finally {
    saving.value = false
  }
}

function onEditorReady({ view: v }) {
  view.value = v
}

// ── Watchers ──────────────────────────────────────────────────────────────────

watch(selectedApp, () => {
  loadTree()
  activeFile.value = null
  editorContent.value = ''
  originalContent.value = ''
})

onMounted(loadApps)
</script>
