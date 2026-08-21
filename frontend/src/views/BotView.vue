<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm">
      <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
        <Send class="w-4 h-4 text-blue-600" />
        Telegram 机器人指令调试与订阅分发
      </h3>
      <p class="text-xs text-slate-500 mt-1">
        在线模拟与调试 Telegram Bot 指令交互（如 /start, /today, /subscribe, /stats），测试即时推送与消息模版渲染。
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Bot Interactive Sandbox -->
      <div class="bg-white rounded-xl p-6 border border-slate-200/80 shadow-sm space-y-4">
        <h4 class="font-bold text-slate-800 text-sm flex items-center gap-2">
          <Terminal class="w-4 h-4 text-slate-700" />
          Bot 模拟交互终端 (Interactive Simulator)
        </h4>

        <!-- Preset Quick Command Chips -->
        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1.5">快捷模拟指令</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="cmd in quickCommands"
              :key="cmd.command"
              @click="selectCommand(cmd)"
              class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-mono font-medium transition-colors"
            >
              {{ cmd.command }} ({{ cmd.desc }})
            </button>
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">指令内容</label>
          <input
            v-model="inputCommand"
            type="text"
            placeholder="/today 或 /subscribe"
            class="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white font-mono"
          />
        </div>

        <button
          @click="sendBotCommand"
          :disabled="sending"
          class="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Send class="w-3.5 h-3.5" />
          <span>{{ sending ? '正在模拟请求与渲染...' : '发送指令测试' }}</span>
        </button>

        <!-- Bot Chat Preview Box -->
        <div v-if="botResponse" class="mt-4 p-4 bg-slate-900 rounded-xl text-slate-100 space-y-2 font-mono text-xs">
          <div class="flex items-center justify-between text-slate-400 text-[11px] pb-2 border-b border-slate-800">
            <span>Bot Response [HTML / Markdown]</span>
            <span class="text-emerald-400">200 OK</span>
          </div>
          <div class="whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto pr-2 text-slate-200">
            {{ botResponse.reply_text || botResponse.response || botResponse }}
          </div>
        </div>
      </div>

      <!-- Telegram Bot Subscription Strategy & Config -->
      <div class="space-y-4">
        <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm space-y-3">
          <h4 class="font-bold text-slate-800 text-xs flex items-center gap-2">
            <CheckCircle2 class="w-4 h-4 text-emerald-600" />
            推送过滤与质量策略
          </h4>
          <div class="space-y-2 text-xs text-slate-600">
            <div class="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg">
              <span>仅推送五星/四星对口岗位 (≥4星)</span>
              <span class="text-emerald-600 font-bold">已启用 (默认)</span>
            </div>
            <div class="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg">
              <span>自动过滤合同制/派遣/非编制岗位</span>
              <span class="text-emerald-600 font-bold">已启用</span>
            </div>
            <div class="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg">
              <span>免笔试/高层次引进特别高亮提醒</span>
              <span class="text-indigo-600 font-bold">已启用</span>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-tr from-slate-900 to-indigo-950 text-white rounded-xl p-5 shadow-md space-y-3">
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-sm">频道与订阅者直连</h4>
            <span class="px-2 py-0.5 rounded-full text-[10px] bg-blue-500/20 text-blue-300 font-bold">TELEGRAM API</span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed">
            支持无缝绑定 Telegram Channel 广播频道或群组，每日早晚定期聚合推送全国最新优质公卫/疾控招考简报。
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Send, Terminal, CheckCircle2 } from 'lucide-vue-next'
import { testBotCommand } from '@/api'

const sending = ref(false)
const inputCommand = ref('/today')
const botResponse = ref(null)

const quickCommands = [
  { command: '/today', desc: '今日优质公卫招考' },
  { command: '/stats', desc: '全国招考大盘' },
  { command: '/subscribe', desc: '订阅省份设置' },
  { command: '/help', desc: '帮助菜单' }
]

const selectCommand = (cmd) => {
  inputCommand.value = cmd.command
  sendBotCommand()
}

const sendBotCommand = async () => {
  if (!inputCommand.value) return
  try {
    sending.value = true
    const res = await testBotCommand({
      command: inputCommand.value,
      chat_id: 123456789
    })
    botResponse.value = res
  } catch (err) {
    botResponse.value = { reply_text: `执行出错: ${err.message}` }
  } finally {
    sending.value = false
  }
}
</script>
