<script setup lang="ts">
import { ref } from 'vue'
import { Play, Square, Zap, KeyRound } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import { getApiKey, setApiKey } from '@/api/http'

const props = defineProps<{
  workflowName: string
}>()

const execution = useExecutionStore()
const message = ref('')
const sessionId = ref('demo-' + Date.now().toString(36))
const showApiKey = ref(false)
const apiKey = ref(getApiKey())

function runStream() {
  if (!message.value.trim()) return
  execution.stream(props.workflowName, message.value, sessionId.value)
}

function runSync() {
  if (!message.value.trim()) return
  execution.execute(props.workflowName, message.value, sessionId.value)
}

function stop() {
  execution.stop()
}

function saveApiKey() {
  setApiKey(apiKey.value)
  showApiKey.value = false
}
</script>

<template>
  <div class="border-t border-zinc-200 bg-white px-4 py-3">
    <div class="flex items-center gap-3">
      <input
        v-model="message"
        placeholder="输入测试消息，如：武汉今天天气怎么样？"
        class="flex-1 rounded-lg bg-white border border-zinc-300 px-4 py-2 text-sm text-zinc-900 focus:border-accent-cyan outline-none placeholder:text-zinc-400"
        @keyup.enter="runStream"
      />

      <input
        v-model="sessionId"
        placeholder="session_id"
        class="w-40 rounded-lg bg-white border border-zinc-300 px-3 py-2 text-xs text-zinc-700 font-mono focus:border-accent-cyan outline-none"
      />

      <template v-if="!execution.isRunning">
        <button
          @click="runStream"
          class="flex items-center gap-1.5 rounded-lg bg-accent-cyan/20 border border-accent-cyan/40 px-4 py-2 text-sm text-accent-cyan hover:bg-accent-cyan/30 transition"
        >
          <Zap :size="15" /> 流式执行
        </button>
        <button
          @click="runSync"
          class="flex items-center gap-1.5 rounded-lg bg-zinc-100 border border-zinc-300 px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-200 transition"
        >
          <Play :size="15" /> 同步执行
        </button>
      </template>

      <button
        v-else
        @click="stop"
        class="flex items-center gap-1.5 rounded-lg bg-accent-red/20 border border-accent-red/40 px-4 py-2 text-sm text-accent-red hover:bg-accent-red/30 transition"
      >
        <Square :size="15" /> 停止
      </button>

      <button
        @click="showApiKey = !showApiKey"
        class="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-500 hover:text-zinc-900 transition"
        title="API Key"
      >
        <KeyRound :size="15" />
      </button>
    </div>

    <!-- API Key 输入 -->
    <div v-if="showApiKey" class="mt-2 flex items-center gap-2">
      <input
        v-model="apiKey"
        type="password"
        placeholder="X-API-Key (可选)"
        class="flex-1 rounded bg-white border border-zinc-300 px-3 py-1.5 text-xs text-zinc-900 font-mono outline-none focus:border-accent-cyan"
      />
      <button @click="saveApiKey" class="rounded bg-accent-cyan/20 border border-accent-cyan/40 px-3 py-1.5 text-xs text-accent-cyan hover:bg-accent-cyan/30">保存</button>
    </div>

    <!-- 执行结果 -->
    <div v-if="execution.error" class="mt-2 rounded border border-accent-red/40 bg-accent-red/10 px-3 py-1.5 text-xs text-accent-red">
      {{ execution.error }}
    </div>
    <div v-else-if="execution.result" class="mt-2 rounded border border-accent-green/40 bg-accent-green/10 px-3 py-1.5 text-xs text-accent-green">
      {{ execution.result }}
    </div>
  </div>
</template>
