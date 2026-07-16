<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Activity } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'

const execution = useExecutionStore()
const expandedKeys = ref<Set<string>>(new Set())

const stateEntries = computed(() => {
  return Object.entries(execution.stateSnapshot).map(([key, value]) => ({
    key,
    value,
    type: Array.isArray(value) ? 'list' : typeof value,
    display: typeof value === 'object' && value !== null ? JSON.stringify(value, null, 2) : String(value),
  }))
})

function toggle(key: string) {
  if (expandedKeys.value.has(key)) expandedKeys.value.delete(key)
  else expandedKeys.value.add(key)
  expandedKeys.value = new Set(expandedKeys.value)
}

function formatValue(val: any): string {
  if (val === null) return 'null'
  if (val === undefined) return 'undefined'
  if (typeof val === 'string' && val.length > 100) return val.slice(0, 100) + '...'
  return String(val)
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex items-center gap-2 border-b border-zinc-200 px-4 py-3">
      <Activity :size="16" class="text-accent-green" />
      <span class="text-sm font-medium text-zinc-900">状态检查器</span>
    </div>

    <div class="flex-1 overflow-y-auto p-3">
      <div v-if="stateEntries.length === 0" class="text-zinc-500 text-sm text-center py-8">
        执行工作流后，状态字段将在此实时展示
      </div>

      <div v-else class="space-y-1.5">
        <div
          v-for="entry in stateEntries"
          :key="entry.key"
          class="rounded border border-zinc-200 bg-white overflow-hidden"
        >
          <div
            class="flex items-center justify-between px-3 py-1.5 cursor-pointer hover:bg-zinc-50"
            @click="toggle(entry.key)"
          >
            <span class="text-xs font-mono text-accent-cyan">{{ entry.key }}</span>
            <div class="flex items-center gap-2">
              <span class="text-[10px] text-zinc-500">{{ entry.type }}</span>
              <span v-if="entry.type !== 'object'" class="text-xs text-zinc-700 font-mono truncate max-w-[200px]">{{ formatValue(entry.value) }}</span>
            </div>
          </div>
          <div v-if="expandedKeys.has(entry.key) && entry.type === 'object'" class="border-t border-zinc-200 p-2">
            <pre class="text-xs text-zinc-700 font-mono whitespace-pre-wrap">{{ entry.display }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
