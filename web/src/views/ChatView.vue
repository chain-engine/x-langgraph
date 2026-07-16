<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Send, Square, Trash2, ArrowLeft, Sparkles, Circle } from 'lucide-vue-next'
import { useChatStore } from '@/stores/chat'
import { useWorkflowStore } from '@/stores/workflow'
import { getApiKey, setApiKey } from '@/api/http'

const router = useRouter()
const route = useRoute()
const chat = useChatStore()
const workflowStore = useWorkflowStore()

const message = ref('')
const showApiKey = ref(false)
const apiKey = ref(getApiKey())
const messagesContainer = ref<HTMLElement | null>(null)
const showStreamToggle = ref(true)
const useStream = ref(true)

const workflowOptions = computed(() => {
  return workflowStore.list.map((w) => ({ value: w.name, label: w.name }))
})

import { computed } from 'vue'

onMounted(() => {
  workflowStore.fetchList()
  const wf = (route.query.workflow as string) || 'simple_router'
  chat.setWorkflow(wf)
})

watch(chat.messages, async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}, { deep: true })

function sendMessage() {
  if (!message.value.trim() || chat.isStreaming) return
  const msg = message.value.trim()
  message.value = ''
  if (useStream.value) {
    chat.sendStream(msg)
  } else {
    chat.send(msg)
  }
}

function stopStreaming() {
  chat.stop()
}

function clearChat() {
  chat.clear()
}

function saveApiKey() {
  setApiKey(apiKey.value)
  showApiKey.value = false
}

function goBack() {
  router.push('/')
}

function selectWorkflow(wf: string) {
  chat.setWorkflow(wf)
}

function getNodeColor(node?: string) {
  if (!node) return 'bg-zinc-400'
  const colors: Record<string, string> = {
    router: 'bg-accent-violet',
    search: 'bg-accent-green',
    calculate: 'bg-accent-cyan',
    weather: 'bg-accent-amber',
    unknown: 'bg-accent-red',
    submit: 'bg-accent-violet',
    evaluate: 'bg-accent-cyan',
    human_approval: 'bg-accent-amber',
    auto_approve: 'bg-accent-green',
    notify: 'bg-accent-violet',
  }
  return colors[node] || 'bg-zinc-400'
}
</script>

<template>
  <div class="h-screen flex flex-col bg-zinc-50">
    <header class="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-3">
      <div class="flex items-center gap-3">
        <button @click="goBack" class="rounded-lg border border-zinc-300 p-2 text-zinc-500 hover:text-zinc-900 hover:border-zinc-400 transition">
          <ArrowLeft :size="18" />
        </button>
        <div>
          <h1 class="text-lg font-medium text-zinc-900">对话模式</h1>
          <p class="text-xs text-zinc-500">使用 /chat 接口进行聊天</p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <select
          v-model="chat.currentWorkflow"
          @change="selectWorkflow(chat.currentWorkflow)"
          class="rounded-lg bg-white border border-zinc-300 px-3 py-1.5 text-sm text-zinc-700 focus:border-accent-cyan outline-none"
        >
          <option v-for="wf in workflowOptions" :key="wf.value" :value="wf.value">
            {{ wf.label }}
          </option>
        </select>

        <button
          v-if="chat.isStreaming"
          @click="stopStreaming"
          class="flex items-center gap-1.5 rounded-lg bg-accent-red/20 border border-accent-red/40 px-3 py-1.5 text-xs text-accent-red hover:bg-accent-red/30 transition"
        >
          <Square :size="14" /> 停止
        </button>
        <button
          v-else
          @click="clearChat"
          class="flex items-center gap-1.5 rounded-lg border border-zinc-300 px-3 py-1.5 text-xs text-zinc-600 hover:text-zinc-900 transition"
        >
          <Trash2 :size="14" /> 清空
        </button>

        <button
          @click="showApiKey = !showApiKey"
          class="rounded-lg border border-zinc-300 px-3 py-1.5 text-zinc-500 hover:text-zinc-900 transition"
          title="API Key"
        >
          <Circle :size="14" />
        </button>
      </div>
    </header>

    <div v-if="showApiKey" class="border-b border-zinc-200 bg-white px-4 py-2">
      <div class="flex items-center gap-2">
        <input
          v-model="apiKey"
          type="password"
          placeholder="X-API-Key"
          class="flex-1 max-w-md rounded bg-white border border-zinc-300 px-3 py-1.5 text-xs text-zinc-900 font-mono outline-none focus:border-accent-cyan"
        />
        <button @click="saveApiKey" class="rounded bg-accent-cyan/20 border border-accent-cyan/40 px-3 py-1.5 text-xs text-accent-cyan hover:bg-accent-cyan/30">保存</button>
      </div>
    </div>

    <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
      <div v-if="chat.messages.length === 0" class="flex flex-col items-center justify-center h-full text-center">
        <Sparkles class="mb-4 text-zinc-400" :size="48" />
        <p class="text-zinc-500">选择工作流并发送消息开始对话</p>
        <p class="mt-2 text-xs text-zinc-400">支持 simple_router 和 approval 工作流</p>
      </div>

      <div
        v-for="msg in chat.messages"
        :key="msg.id"
        class="flex gap-3"
        :class="msg.role === 'user' ? 'flex-row-reverse' : ''"
      >
        <div
          class="flex-shrink-0 rounded-full p-2"
          :class="msg.role === 'user' ? 'bg-accent-cyan' : 'bg-accent-violet'"
        >
          <span class="text-xs font-bold text-white">{{ msg.role === 'user' ? '你' : 'AI' }}</span>
        </div>

        <div class="max-w-[70%]">
          <div
            class="rounded-2xl px-4 py-2.5 text-sm"
            :class="msg.role === 'user' 
              ? 'rounded-tr-sm bg-accent-cyan/20 text-zinc-900' 
              : 'rounded-tl-sm bg-zinc-100 text-zinc-700'"
          >
            {{ msg.content }}
          </div>

          <div v-if="msg.node" class="mt-1 flex items-center gap-1.5">
            <span
              class="inline-flex h-2 w-2 rounded-full"
              :class="getNodeColor(msg.node)"
            ></span>
            <span class="text-[10px] text-zinc-400 font-mono">{{ msg.node }}</span>
          </div>

          <div class="mt-1 text-[10px] text-zinc-400">
            {{ msg.timestamp.toLocaleTimeString('zh-CN') }}
          </div>
        </div>
      </div>

      <div v-if="chat.isStreaming" class="flex items-center gap-2">
        <div class="flex-shrink-0 rounded-full bg-accent-violet p-2">
          <span class="text-xs font-bold text-white">AI</span>
        </div>
        <div class="rounded-2xl rounded-tl-sm bg-zinc-100 px-4 py-2.5">
          <div class="flex items-center gap-1.5 text-sm text-zinc-500">
            <span class="h-2 w-2 animate-bounce rounded-full bg-accent-cyan"></span>
            <span class="h-2 w-2 animate-bounce rounded-full bg-accent-cyan" style="animation-delay: 0.1s"></span>
            <span class="h-2 w-2 animate-bounce rounded-full bg-accent-cyan" style="animation-delay: 0.2s"></span>
            <span class="ml-1">正在响应...</span>
          </div>
        </div>
      </div>
    </div>

    <footer class="border-t border-zinc-200 bg-white px-4 py-3">
      <div class="flex items-center gap-3">
        <div v-if="showStreamToggle" class="flex items-center gap-2">
          <button
            @click="useStream = true"
            class="rounded-lg px-3 py-2 text-xs transition"
            :class="useStream ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-zinc-100 text-zinc-500'"
          >
            流式
          </button>
          <button
            @click="useStream = false"
            class="rounded-lg px-3 py-2 text-xs transition"
            :class="!useStream ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-zinc-100 text-zinc-500'"
          >
            同步
          </button>
        </div>

        <input
          v-model="message"
          placeholder="输入消息..."
          class="flex-1 rounded-lg bg-white border border-zinc-300 px-4 py-2 text-sm text-zinc-900 focus:border-accent-cyan outline-none placeholder:text-zinc-400"
          @keyup.enter="sendMessage"
          :disabled="chat.isStreaming"
        />

        <button
          @click="sendMessage"
          :disabled="!message.trim() || chat.isStreaming"
          class="flex items-center gap-1.5 rounded-lg bg-accent-cyan/20 border border-accent-cyan/40 px-4 py-2 text-sm text-accent-cyan hover:bg-accent-cyan/30 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send :size="15" /> 发送
        </button>
      </div>

      <div class="mt-2 flex items-center justify-between text-[10px] text-zinc-400">
        <span>Session ID: {{ chat.currentSessionId }}</span>
        <span>最后执行节点: {{ chat.lastNode || '-' }}</span>
      </div>
    </footer>
  </div>
</template>
