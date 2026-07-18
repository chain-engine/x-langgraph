<script setup lang="ts">
import { GitBranch, Cog, Wrench, HelpCircle } from 'lucide-vue-next'

const nodeTypes = [
  {
    type: 'processor',
    label: 'Processor',
    description: '处理消息的节点',
    icon: Cog,
    borderClass: 'border-accent-cyan',
    iconClass: 'text-accent-cyan',
  },
  {
    type: 'router',
    label: 'Router',
    description: '路由分发到多个分支',
    icon: GitBranch,
    borderClass: 'border-accent-violet',
    iconClass: 'text-accent-violet',
  },
  {
    type: 'tool',
    label: 'Tool',
    description: '调用外部工具',
    icon: Wrench,
    borderClass: 'border-accent-green',
    iconClass: 'text-accent-green',
  },
  {
    type: 'unknown',
    label: 'Unknown',
    description: '未知类型节点',
    icon: HelpCircle,
    borderClass: 'border-accent-red',
    iconClass: 'text-accent-red',
  },
]

function onDragStart(event: DragEvent, nodeType: string) {
  event.dataTransfer?.setData('application/x-workflow-node-type', nodeType)
  event.dataTransfer!.effectAllowed = 'move'
}
</script>

<template>
  <div class="p-3 border-b border-zinc-200">
    <h3 class="text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wide">添加节点</h3>
    <div class="space-y-1.5">
      <div
        v-for="t in nodeTypes"
        :key="t.type"
        draggable="true"
        @dragstart="onDragStart($event, t.type)"
        class="flex items-center gap-2.5 rounded-lg border-2 px-3 py-2 cursor-grab active:cursor-grabbing hover:shadow-sm transition-all hover:-translate-y-0.5"
        :class="t.borderClass"
      >
        <component :is="t.icon" :size="14" :class="t.iconClass" />
        <div class="flex flex-col">
          <span class="text-xs font-medium text-zinc-900">{{ t.label }}</span>
          <span class="text-[10px] text-zinc-400">{{ t.description }}</span>
        </div>
      </div>
    </div>
    <p class="text-[10px] text-zinc-400 mt-2">拖拽到画布添加节点</p>
  </div>
</template>
