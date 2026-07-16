<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { GitBranch, Cog, Wrench, HelpCircle, CircleStop } from 'lucide-vue-next'

const props = defineProps<{
  id: string
  data: {
    label: string
    nodeType: string
    handler: string
    config: Record<string, any>
    status?: string
    isEntryPoint?: boolean
  }
}>()

const colors = {
  router: { border: 'border-accent-violet', bg: 'bg-white', icon: GitBranch, iconColor: 'text-accent-violet' },
  processor: { border: 'border-accent-cyan', bg: 'bg-white', icon: Cog, iconColor: 'text-accent-cyan' },
  tool: { border: 'border-accent-green', bg: 'bg-white', icon: Wrench, iconColor: 'text-accent-green' },
  unknown: { border: 'border-accent-red', bg: 'bg-white', icon: HelpCircle, iconColor: 'text-accent-red' },
  end: { border: 'border-zinc-400', bg: 'bg-zinc-50', icon: CircleStop, iconColor: 'text-zinc-500' },
}

const style = computed(() => colors[props.data.nodeType as keyof typeof colors] || colors.processor)
const statusClass = computed(() => {
  switch (props.data.status) {
    case 'running': return 'animate-pulse-glow border-accent-cyan'
    case 'completed': return 'border-accent-green'
    case 'error': return 'border-accent-red'
    default: return ''
  }
})
</script>

<template>
  <div
    class="relative flex items-center gap-2 rounded-lg border-2 px-4 py-2.5 min-w-[140px] transition-all"
    :class="[style.bg, style.border, statusClass]"
  >
    <Handle type="target" :position="Position.Left" class="!bg-zinc-400 !border-none !w-2.5 !h-2.5" />

    <component :is="style.icon" :size="16" :class="style.iconColor" />
    <div class="flex flex-col">
      <span class="text-sm font-medium text-zinc-900">{{ data.label }}</span>
      <span class="text-xs text-zinc-500 font-mono">{{ data.handler }}</span>
    </div>

    <span
      v-if="data.isEntryPoint"
      class="absolute -top-2 -right-2 rounded-full bg-accent-amber px-1.5 py-0.5 text-[10px] font-bold text-white"
    >START</span>

    <Handle type="source" :position="Position.Right" class="!bg-zinc-400 !border-none !w-2.5 !h-2.5" />
  </div>
</template>
