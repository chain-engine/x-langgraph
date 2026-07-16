<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Trash2, Workflow, Search, KeyRound } from 'lucide-vue-next'
import { useWorkflowStore } from '@/stores/workflow'
import { getApiKey, setApiKey } from '@/api/http'

const router = useRouter()
const store = useWorkflowStore()
const showNew = ref(false)
const showApiKey = ref(false)
const apiKey = ref(getApiKey())
const newName = ref('')
const newDesc = ref('')
const searchQuery = ref('')

const filtered = computed(() => {
  if (!searchQuery.value) return store.list
  const q = searchQuery.value.toLowerCase()
  return store.list.filter((w) => w.name.toLowerCase().includes(q) || w.description.toLowerCase().includes(q))
})

onMounted(() => store.fetchList())

function openEditor(name: string) {
  router.push(`/editor/${name}`)
}

function createWorkflow() {
  if (!newName.value.trim()) return
  const name = newName.value.trim()
  store.saveWorkflow({
    name,
    description: newDesc.value,
    state_schema: { input: 'str', output: 'str', error: 'Optional[str]' },
    graph_data: { nodes: [], edges: [], entry_point: '' },
  }).then(() => {
    showNew.value = false
    newName.value = ''
    newDesc.value = ''
    openEditor(name)
  })
}

async function deleteWorkflow(name: string, e: Event) {
  e.stopPropagation()
  await store.deleteWorkflow(name)
}

function saveApiKey() {
  setApiKey(apiKey.value)
  showApiKey.value = false
}
</script>

<template>
  <div class="min-h-screen bg-base-900">
    <!-- 顶部栏 -->
    <header class="border-b border-base-500 bg-base-800 px-6 py-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <Workflow :size="24" class="text-accent-cyan" />
          <div>
            <h1 class="text-lg font-bold text-zinc-100">工作流可视化平台</h1>
            <p class="text-xs text-zinc-500">x-langgraph Workflow Visualizer</p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="showApiKey = !showApiKey"
            class="flex items-center gap-1.5 rounded-lg border border-base-400 px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-200 transition"
          >
            <KeyRound :size="14" /> API Key
          </button>
          <button
            @click="showNew = true"
            class="flex items-center gap-1.5 rounded-lg bg-accent-cyan/20 border border-accent-cyan/40 px-4 py-1.5 text-sm text-accent-cyan hover:bg-accent-cyan/30 transition"
          >
            <Plus :size="15" /> 新建工作流
          </button>
        </div>
      </div>

      <!-- API Key 输入 -->
      <div v-if="showApiKey" class="mt-3 flex items-center gap-2">
        <input
          v-model="apiKey"
          type="password"
          placeholder="X-API-Key（后端未设置 API_KEY 时可留空）"
          class="flex-1 rounded bg-base-900 border border-base-500 px-3 py-1.5 text-xs text-zinc-100 font-mono outline-none focus:border-accent-cyan"
        />
        <button @click="saveApiKey" class="rounded bg-accent-cyan/20 border border-accent-cyan/40 px-3 py-1.5 text-xs text-accent-cyan">保存</button>
      </div>
    </header>

    <!-- 搜索栏 -->
    <div class="px-6 py-4">
      <div class="relative max-w-md">
        <Search :size="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
        <input
          v-model="searchQuery"
          placeholder="搜索工作流..."
          class="w-full rounded-lg bg-base-800 border border-base-500 pl-9 pr-3 py-2 text-sm text-zinc-100 outline-none focus:border-accent-cyan"
        />
      </div>
    </div>

    <!-- 工作流卡片网格 -->
    <div class="px-6 pb-8">
      <div v-if="store.loading" class="text-zinc-500 text-sm py-12 text-center">加载中...</div>

      <div v-else-if="filtered.length === 0" class="text-zinc-600 text-sm py-12 text-center">
        暂无工作流，点击右上角「新建工作流」创建
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="wf in filtered"
          :key="wf.name"
          @click="openEditor(wf.name)"
          class="group cursor-pointer rounded-xl border border-base-500 bg-base-800 p-5 hover:border-accent-cyan/50 hover:bg-base-700 transition-all"
        >
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-2">
              <div class="w-10 h-10 rounded-lg bg-accent-violet/20 flex items-center justify-center">
                <Workflow :size="20" class="text-accent-violet" />
              </div>
              <div>
                <h3 class="text-sm font-bold text-zinc-100">{{ wf.name }}</h3>
                <p class="text-xs text-zinc-500">{{ wf.node_count }} 节点 · {{ wf.edge_count }} 边</p>
              </div>
            </div>
            <button
              @click="deleteWorkflow(wf.name, $event)"
              class="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-accent-red transition"
            >
              <Trash2 :size="15" />
            </button>
          </div>
          <p class="mt-3 text-xs text-zinc-400 line-clamp-2">{{ wf.description || '无描述' }}</p>
        </div>
      </div>
    </div>

    <!-- 新建弹窗 -->
    <div v-if="showNew" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60" @click.self="showNew = false">
      <div class="w-96 rounded-xl border border-base-500 bg-base-800 p-6">
        <h2 class="text-base font-bold text-zinc-100 mb-4">新建工作流</h2>
        <div class="space-y-3">
          <div>
            <label class="block text-xs text-zinc-500 mb-1">名称</label>
            <input v-model="newName" placeholder="如：my_workflow" class="w-full rounded bg-base-900 border border-base-500 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-accent-cyan" />
          </div>
          <div>
            <label class="block text-xs text-zinc-500 mb-1">描述</label>
            <input v-model="newDesc" placeholder="工作流描述" class="w-full rounded bg-base-900 border border-base-500 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-accent-cyan" />
          </div>
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button @click="showNew = false" class="rounded border border-base-400 px-4 py-1.5 text-sm text-zinc-400 hover:text-zinc-200">取消</button>
          <button @click="createWorkflow" class="rounded bg-accent-cyan/20 border border-accent-cyan/40 px-4 py-1.5 text-sm text-accent-cyan hover:bg-accent-cyan/30">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>
