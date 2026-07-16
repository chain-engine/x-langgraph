<script setup lang="ts">
import { computed } from 'vue'
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath } from '@vue-flow/core'

const props = defineProps<{
  id: string
  sourceX: number
  sourceY: number
  targetX: number
  targetY: number
  sourcePosition: any
  targetPosition: any
  data?: {
    edgeType: string
    condition?: { field: string; operator: string; value: string }
    isActive?: boolean
  }
}>()

const path = computed(() =>
  getSmoothStepPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
  }),
)

const isConditional = computed(() => props.data?.edgeType === 'conditional')
const isActive = computed(() => props.data?.isActive)

const strokeClass = computed(() => {
  if (isActive.value) return '#00d4ff'
  if (isConditional.value) return '#f59e0b'
  return '#3a3a4a'
})

const dashClass = computed(() => {
  if (isActive.value) return '8 4'
  if (isConditional.value) return '6 4'
  return 'none'
})
</script>

<template>
  <BaseEdge
    :id="id"
    :path="path[0]"
    :style="{
      stroke: strokeClass,
      strokeWidth: isActive ? 3 : 2,
      strokeDasharray: dashClass,
      animation: isActive ? 'flow-dash 0.8s linear infinite' : 'none',
    }"
  />

  <EdgeLabelRenderer v-if="isConditional && data?.condition">
    <div
      :style="{
        position: 'absolute',
        transform: `translate(-50%, -50%) translate(${path[1]}px,${path[2]}px)`,
        pointerEvents: 'all',
      }"
      class="rounded border border-accent-amber/40 bg-base-700 px-2 py-0.5 text-[10px] text-accent-amber font-mono whitespace-nowrap"
    >
      {{ data.condition.field }} {{ data.condition.operator }} "{{ data.condition.value }}"
    </div>
  </EdgeLabelRenderer>
</template>
