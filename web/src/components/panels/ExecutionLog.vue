<script setup lang="ts">
import { computed } from 'vue'
import { ScrollText, Circle, CheckCircle2, XCircle, Loader } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'

const execution = useExecutionStore()

const entries = computed(() => execution.sortedLog)

function eventIcon(event: string) {
  switch (event) {
    case 'done': return CheckCircle2
    case 'error': return XCircle
    case 'node_update': return Circle
    default: return Circle
  }
}

function eventColor(event: string) {
  switch (event) {
    case 'done': return 'text-accent-green'
    case 'error': return 'text-accent-red'
    case 'node_update': return 'text-accent-cyan'
    default: return 'text-zinc-500'
  }
}

function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString('zh-CN', { hour12: false })
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex items-center gap-2 border-b border-zinc-200 px-4 py-3">
      <ScrollText :size="16" class="text-accent-amber" />
      <span class="text-sm font-medium text-zinc-900">执行日志</span>
      <Loader v-if="execution.isRunning" :size="14" class="ml-auto animate-spin text-accent-cyan" />
    </div>

    <div class="flex-1 overflow-y-auto p-3">
      <div v-if="entries.length === 0" class="text-zinc-500 text-sm text-center py-8">
        执行日志将在此显示
      </div>

      <div v-else class="relative pl-6">
        <!-- 时间线竖线 -->
        <div class="absolute left-[10px] top-0 bottom-0 w-px bg-zinc-300" />

        <div v-for="(entry, i) in entries" :key="i" class="relative mb-3">
          <!-- 时间线节点 -->
          <div class="absolute -left-6 top-0.5 flex items-center justify-center w-5 h-5 rounded-full bg-white border border-zinc-300">
            <component :is="eventIcon(entry.event)" :size="10" :class="eventColor(entry.event)" />
          </div>

          <div class="rounded bg-white border border-zinc-200 px-3 py-2">
            <div class="flex items-center justify-between">
              <span v-if="entry.node" class="text-xs font-mono text-accent-violet">{{ entry.node }}</span>
              <span v-else class="text-xs text-zinc-600">{{ entry.event }}</span>
              <span class="text-[10px] text-zinc-400 font-mono">{{ formatTime(entry.timestamp) }}</span>
            </div>
            <div v-if="entry.data" class="mt-1 text-xs text-zinc-700 font-mono truncate">
              {{ typeof entry.data === 'string' ? entry.data : JSON.stringify(entry.data).slice(0, 120) }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
