<template>
  <div>
    <!-- Directory or File Header Row -->
    <div 
      class="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs cursor-pointer select-none transition-colors"
      :class="[
        node.is_dir ? 'text-ink-gray-7 hover:bg-surface-gray-2' : 'hover:bg-surface-gray-2',
        node.path === activePath ? 'bg-indigo-50 text-indigo-700 font-medium hover:bg-indigo-100' : 'text-ink-gray-6'
      ]"
      :style="{ paddingLeft: `${depth * 12 + 8}px` }"
      @click="onClick"
    >
      <!-- Icon -->
      <span v-if="node.is_dir" class="size-3.5 shrink-0" :class="isOpen ? 'lucide-folder-open text-amber-500' : 'lucide-folder text-amber-500'" />
      <span v-else class="size-3.5 shrink-0" :class="fileIcon" />
      
      <!-- Name -->
      <span class="truncate">{{ node.name }}</span>
    </div>

    <!-- Children Nodes (only for directory and when open) -->
    <div v-if="node.is_dir && isOpen && node.children && node.children.length" class="mt-0.5">
      <FileTreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        :active-path="activePath"
        @select-file="$emit('select-file', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
  activePath: { type: String, default: '' }
})

const emit = defineEmits(['select-file'])

const isOpen = ref(false)

const fileIcon = computed(() => {
  const ext = props.node.name.split('.').pop().toLowerCase()
  const icons = {
    py: 'lucide-file-code-2 text-blue-500',
    js: 'lucide-file-json text-yellow-500',
    vue: 'lucide-file-code text-green-500',
    json: 'lucide-file-cog text-rose-500',
    css: 'lucide-file-style text-pink-500',
    html: 'lucide-file-html text-orange-500',
    md: 'lucide-file-text text-gray-500',
    sh: 'lucide-terminal text-teal-600',
  }
  return icons[ext] || 'lucide-file text-gray-400'
})

function onClick() {
  if (props.node.is_dir) {
    isOpen.value = !isOpen.value
  } else {
    emit('select-file', props.node)
  }
}
</script>
