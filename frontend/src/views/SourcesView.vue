<template>
  <div class="space-y-6">
    <!-- Header Controls -->
    <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
          <Globe2 class="w-4 h-4 text-blue-600" />
          全国数据源与爬虫健康度矩阵
        </h3>
        <p class="text-xs text-slate-500 mt-1">
          已纳管 31 个省/直辖市官方卫健委、人社厅与疾控中心，共 {{ sources.length }} 个实时爬虫适配器。
        </p>
      </div>

      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>定时调度器:</span>
          <span class="font-mono font-bold text-slate-700">{{ schedulerStatus?.running ? '运行中 (Running)' : '就绪 (Active)' }}</span>
        </div>
        <button
          @click="loadSources"
          class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
        >
          刷新矩阵
        </button>
      </div>
    </div>

    <!-- Sources Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="source in sources"
        :key="source.source_id"
        class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
      >
        <div>
          <div class="flex items-start justify-between">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-600">
              {{ source.province }}
            </span>
            <span
              class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold"
              :class="source.status === 'ACTIVE' || source.status === 'HEALTHY' || !source.status ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'"
            >
              {{ source.status || 'ACTIVE' }}
            </span>
          </div>

          <h4 class="font-bold text-slate-900 text-sm mt-3">{{ source.name }}</h4>
          <p class="text-xs text-slate-500 font-mono mt-1 break-all truncate" :title="source.url">
            {{ source.url }}
          </p>

          <div class="grid grid-cols-2 gap-2 mt-4 text-[11px] bg-slate-50 p-2.5 rounded-lg">
            <div>
              <span class="text-slate-400">适配器 ID:</span>
              <div class="font-mono font-semibold text-slate-700 truncate">{{ source.source_id }}</div>
            </div>
            <div>
              <span class="text-slate-400">更新周期:</span>
              <div class="font-semibold text-slate-700">每 {{ source.interval_hours || 2 }} 小时</div>
            </div>
          </div>
        </div>

        <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
          <span class="text-[11px] text-slate-400">
            最后成功: {{ source.last_crawled_at ? source.last_crawled_at.slice(0, 16) : '最近已就绪' }}
          </span>
          <button
            @click="triggerCrawl(source.source_id)"
            :disabled="crawlingId === source.source_id"
            class="px-2.5 py-1 bg-blue-50 hover:bg-blue-100 text-blue-600 font-semibold text-xs rounded transition-colors disabled:opacity-50 flex items-center gap-1"
          >
            <RefreshCw class="w-3 h-3" :class="{ 'animate-spin': crawlingId === source.source_id }" />
            <span>{{ crawlingId === source.source_id ? '抓取中...' : '立即采集' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Globe2, RefreshCw } from 'lucide-vue-next'
import { fetchSources, getSchedulerStatus, triggerSourceCrawl } from '@/api'

const sources = ref([])
const schedulerStatus = ref(null)
const crawlingId = ref(null)

const loadSources = async () => {
  try {
    const [srcRes, schRes] = await Promise.all([
      fetchSources(),
      getSchedulerStatus()
    ])
    sources.value = srcRes.sources || srcRes || []
    schedulerStatus.value = schRes
  } catch (err) {
    console.error('Failed to load sources:', err)
  }
}

const triggerCrawl = async (sourceId) => {
  try {
    crawlingId.value = sourceId
    const res = await triggerSourceCrawl(sourceId)
    alert(`触发成功！${res.message || '任务已推入执行队列'}`)
    loadSources()
  } catch (err) {
    alert(`触发失败: ${err.message}`)
  } finally {
    crawlingId.value = null
  }
}

onMounted(() => {
  loadSources()
})
</script>
