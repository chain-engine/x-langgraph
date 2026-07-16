<script setup lang="ts">
import { ref, watch } from 'vue'
import { Settings2, ChevronDown } from 'lucide-vue-next'
import type { NodeDefinition, EdgeDefinition } from '@/types/workflow'

const props = defineProps<{
  node: NodeDefinition | null
  edge: EdgeDefinition | null
}>()

const emit = defineEmits<{
  updateNode: [node: NodeDefinition]
  updateEdge: [edge: EdgeDefinition]
  deleteNode: [nodeId: string]
  deleteEdge: [edgeId: string]
}>()

const form = ref<any>({})

watch(() => props.node, (n) => {
  if (n) form.value = { ...n, position: { ...n.position }, config: { ...n.config } }
}, { immediate: true, deep: true })

watch(() => props.edge, (e) => {
  if (e) form.value = { ...e, condition: e.condition ? { ...e.condition } : { field: '', operator: '==', value: '' } }
}, { immediate: true, deep: true })

function save() {
  if (props.node) emit('updateNode', form.value)
  if (props.edge) emit('updateEdge', form.value)
}

function remove() {
  if (props.node) emit('deleteNode', props.node.id)
  if (props.edge) emit('deleteEdge', props.edge.id)
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex items-center gap-2 border-b border-zinc-200 px-4 py-3">
      <Settings2 :size="16" class="text-accent-cyan" />
      <span class="text-sm font-medium text-zinc-900">属性面板</span>
    </div>

    <div v-if="!node && !edge" class="flex flex-1 items-center justify-center text-zinc-500 text-sm">
      选择一个节点或边查看属性
    </div>

    <!-- 节点属性 -->
    <div v-else-if="node" class="flex-1 overflow-y-auto p-4 space-y-3">
      <div>
        <label class="block text-xs text-zinc-500 mb-1">节点 ID</label>
        <input v-model="form.id" disabled class="w-full rounded bg-zinc-50 border border-zinc-200 px-3 py-1.5 text-sm text-zinc-500 font-mono" />
      </div>
      <div>
        <label class="block text-xs text-zinc-500 mb-1">显示名称</label>
        <input v-model="form.label" class="w-full rounded bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-900 focus:border-accent-cyan outline-none" />
      </div>
      <div>
        <label class="block text-xs text-zinc-500 mb-1">节点类型</label>
        <select v-model="form.type" class="w-full rounded bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-900 focus:border-accent-cyan outline-none">
          <option value="router">router (路由)</option>
          <option value="processor">processor (处理)</option>
          <option value="tool">tool (工具)</option>
          <option value="unknown">unknown (未知)</option>
        </select>
      </div>
      <div>
        <label class="block text-xs text-zinc-500 mb-1">Handler 标识</label>
        <input v-model="form.handler" class="w-full rounded bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-900 font-mono focus:border-accent-cyan outline-none" />
      </div>
      <div>
        <label class="block text-xs text-zinc-500 mb-1">坐标 (X, Y)</label>
        <div class="flex gap-2">
          <input v-model.number="form.position.x" type="number" class="w-1/2 rounded bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-900 focus:border-accent-cyan outline-none" />
          <input v-model.number="form.position.y" type="number" class="w-1/2 rounded bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-900 focus:border-accent-cyan outline-none" />
        </div>
      </div>
      <div>
        <label class="block text-xs text-zinc-500 mb-1">配置 (JSON)</label>
        <textarea
          :value="JSON.stringify(form.config, null, 2)"
          @input="(e) => { try { form.config = JSON.parse((e.target as HTMLTextAreaElement).value || '{}') } catch {} }"
          rows="5"
          class="w-full rounded bg-white border border-zinc-300 px-3 py-1.5 text-xs text-zinc-900 font-mono focus:border-accent-cyan outline-none resize-none"
        />
      </div>

      <div class="flex gap-2 pt-2">
        <button @click="save" class="flex-1 rounded bg-accent-cyan/20 border border-accent-cyan/40 px-3 py-1.5 text-sm text-accent-cyan hover:bg-accent-cyan/30 transition">保存</button>
        <button @click="remove" class="rounded border border-accent-red/40 px-3 py-1.5 text-sm text-accent-red hover:bg-accent-red/20 transition">删除</button>
      </div>
    </div>

    <!-- 边属性 -->
    <div v-else-if="edge" class="flex-1 overflow-y-auto p-4 space-y-3">
      <div>
        <label class="block text-xs text-zinc-500 mb-1">边 ID</label>
        <input v-model="form.id" disabled class="w-full rounded bg-zinc-50 border border-zinc-200 px-3 py-1.5 text-sm text-zinc-500 font-mono" />
      </div>
      <div>
        <label class="block text-xs text-zinc-500 mb-1">源节点 → 目标节点</label>
        <div class="flex items-center gap-2 text-sm text-zinc-700 font-mono">
          <span class="rounded bg-zinc-100 px-2 py-1">{{ form.source }}</span>
          <span class="text-zinc-400">→</span>
          <span class="rounded bg-zinc-100 px-2 py-1">{{ form.target }}</span>
        </div>
      </div>
      <div>
        <label class="block text-xs text-zinc-500 mb-1">边类型</label>
        <select v-model="form.type" class="w-full rounded bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-900 focus:border-accent-cyan outline-none">
          <option value="normal">normal (普通边)</option>
          <option value="conditional">conditional (条件边)</option>
        </select>
      </div>
      <div v-if="form.type === 'conditional'">
        <label class="block text-xs text-zinc-500 mb-1">条件表达式</label>
        <div class="space-y-2">
          <input v-model="form.condition.field" placeholder="字段名 (如 route)" class="w-full rounded bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-900 font-mono focus:border-accent-cyan outline-none" />
          <select v-model="form.condition.operator" class="w-full rounded bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-900 focus:border-accent-cyan outline-none">
            <option value="==">== (等于)</option>
            <option value="!=">!= (不等于)</option>
            <option value="in">in (包含)</option>
            <option value="not_in">not_in (不包含)</option>
          </select>
          <input v-model="form.condition.value" placeholder="值 (如 search)" class="w-full rounded bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-900 font-mono focus:border-accent-cyan outline-none" />
        </div>
      </div>

      <div class="flex gap-2 pt-2">
        <button @click="save" class="flex-1 rounded bg-accent-cyan/20 border border-accent-cyan/40 px-3 py-1.5 text-sm text-accent-cyan hover:bg-accent-cyan/30 transition">保存</button>
        <button @click="remove" class="rounded border border-accent-red/40 px-3 py-1.5 text-sm text-accent-red hover:bg-accent-red/20 transition">删除</button>
      </div>
    </div>
  </div>
</template>
