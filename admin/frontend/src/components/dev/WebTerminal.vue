<template>
  <div class="relative w-full h-full overflow-hidden flex flex-col transition-colors duration-150" :class="isDark ? 'bg-[#0f172a]' : 'bg-white'" @click="term && term.focus()">
    <!-- Terminal View Container -->
    <div ref="terminalRef" class="flex-1 min-h-0 w-full" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch, computed } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { useTheme } from 'frappe-ui'
import { terminalApi } from '@/api/terminal'

const terminalRef = ref(null)
const sessionId = ref('')
const eventSource = ref(null)

const { theme } = useTheme()
const isDark = computed(() => {
  if (theme.value === 'system') {
    return document.documentElement.classList.contains('dark')
  }
  return theme.value === 'dark'
})

let term = null
let fitAddon = null
let resizeObserver = null

// Helper to convert hex encoded output stream to bytes array
function hexToBytes(hex) {
  const len = hex.length
  const bytes = new Uint8Array(len / 2)
  for (let i = 0; i < len; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16)
  }
  return bytes
}

// Helper to convert input string bytes to hex
function bytesToHex(bytes) {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

const getThemeOptions = (dark) => ({
  background: dark ? '#0f172a' : '#ffffff',
  foreground: dark ? '#e2e8f0' : '#1e293b',
  cursor: dark ? '#94a3b8' : '#1e293b',
  black: dark ? '#020617' : '#ffffff',
  red: '#ef4444',
  green: '#22c55e',
  yellow: '#eab308',
  blue: '#3b82f6',
  magenta: '#a855f7',
  cyan: '#06b6d4',
  white: dark ? '#cbd5e1' : '#0f172a',
})

watch(isDark, (val) => {
  if (term) {
    term.options.theme = getThemeOptions(val)
  }
})

async function initTerminal() {
  if (!terminalRef.value) return

  // 1. Initialize Terminal instance
  term = new Terminal({
    theme: getThemeOptions(isDark.value),
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
    fontSize: 13,
    lineHeight: 1.3,
    cursorBlink: true,
    scrollback: 2000,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)

  // Open xterm on mount
  term.open(terminalRef.value)
  fitAddon.fit()
  term.focus()

  try {
    // 2. Create Backend PTY Session
    const res = await terminalApi.createSession()
    sessionId.value = res.session_id

    // 3. Connect output stream (SSE)
    const streamUrl = terminalApi.getStreamUrl(res.session_id)
    eventSource.value = new EventSource(streamUrl)

    eventSource.value.onmessage = (event) => {
      const bytes = hexToBytes(event.data)
      term.write(bytes)
    }

    eventSource.value.onerror = () => {
      term.write('\r\n\x1b[31m[Connection lost or session closed]\x1b[0m\r\n')
      cleanupSession()
    }

    // 4. Hook input event handler
    term.onData((data) => {
      if (!sessionId.value) return
      const hex = bytesToHex(new TextEncoder().encode(data))
      terminalApi.sendInput(sessionId.value, hex).catch(() => {})
    })

    // 5. Send initial terminal dimensions
    await terminalApi.resize(sessionId.value, term.cols, term.rows)

    // 6. Set up ResizeObserver to handle element size changes dynamically
    resizeObserver = new ResizeObserver(() => {
      if (term && fitAddon && sessionId.value) {
        fitAddon.fit()
        terminalApi.resize(sessionId.value, term.cols, term.rows).catch(() => {})
      }
    })
    resizeObserver.observe(terminalRef.value)

  } catch (err) {
    term.write(`\r\n\x1b[31mFailed to start shell session: ${err.message || err}\x1b[0m\r\n`)
  }
}

function cleanupSession() {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
  sessionId.value = ''
}

onMounted(initTerminal)

onBeforeUnmount(() => {
  cleanupSession()
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  if (term) {
    term.dispose()
  }
})
</script>

<style>
.xterm, 
.xterm .xterm-screen, 
.xterm .xterm-viewport,
.xterm-viewport,
.xterm-screen {
  background-color: transparent !important;
}
</style>
