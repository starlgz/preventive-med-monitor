<template>
  <div class="space-y-6">
    <!-- Top Bar & Tabs -->
    <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
          <Globe2 class="w-4 h-4 text-blue-600" />
          招考数据源与低代码爬虫引擎
        </h3>
        <p class="text-xs text-slate-500 mt-1">
          已纳管官方内置源 {{ sources.length }} 个，自定义低代码爬虫 {{ customSources.length }} 个。
        </p>
      </div>

      <div class="flex items-center gap-3 flex-wrap">
        <!-- Tab Switch -->
        <div class="bg-slate-100 p-1 rounded-lg flex items-center gap-1 text-xs">
          <button
            @click="activeTab = 'builtin'"
            class="px-3 py-1.5 rounded-md font-semibold transition-all"
            :class="activeTab === 'builtin' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
          >
            内置官方源 ({{ sources.length }})
          </button>
          <button
            @click="activeTab = 'custom'"
            class="px-3 py-1.5 rounded-md font-semibold transition-all flex items-center gap-1.5"
            :class="activeTab === 'custom' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
          >
            <Sparkles class="w-3.5 h-3.5 text-amber-500" />
            自定义爬虫 ({{ customSources.length }})
          </button>
        </div>

        <button
          v-if="activeTab === 'custom'"
          @click="openCreateModal"
          class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1 shadow-sm shadow-blue-500/20"
        >
          <Plus class="w-3.5 h-3.5" />
          新建爬虫
        </button>

        <button
          @click="loadAllData"
          class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
        >
          刷新
        </button>
      </div>
    </div>

    <!-- TAB 1: Builtin Sources Grid -->
    <div v-if="activeTab === 'builtin'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
            最后抓取: {{ source.last_crawled_at ? source.last_crawled_at.slice(0, 16) : '最近已就绪' }}
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

    <!-- TAB 2: Custom Low-code Sources Grid -->
    <div v-if="activeTab === 'custom'">
      <div v-if="customSources.length === 0" class="bg-white rounded-xl p-12 text-center border border-slate-200/80">
        <div class="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3">
          <Sparkles class="w-6 h-6" />
        </div>
        <h4 class="text-slate-800 font-bold text-sm">暂无自定义低代码爬虫</h4>
        <p class="text-slate-500 text-xs mt-1 max-w-sm mx-auto">
          你可以点击右上角「新建爬虫」，无需编写代码，输入目标招考网站 URL 与 CSS 选择器即可秒级接入采集。
        </p>
        <button
          @click="openCreateModal"
          class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm"
        >
          立即创建第一个自定义爬虫
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="cs in customSources"
          :key="cs.source_key"
          class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <div class="flex items-start justify-between">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200/50">
                {{ cs.province }} · {{ cs.protocol.toUpperCase() }}
              </span>
              <span
                class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold"
                :class="cs.is_active ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'"
              >
                {{ cs.is_active ? '已启用' : '已停用' }}
              </span>
            </div>

            <h4 class="font-bold text-slate-900 text-sm mt-3 flex items-center gap-1.5">
              <span>{{ cs.name }}</span>
            </h4>
            <p class="text-xs text-slate-500 font-mono mt-1 break-all truncate" :title="cs.rule?.url">
              {{ cs.rule?.url }}
            </p>

            <div class="mt-4 text-[11px] bg-slate-50 p-2.5 rounded-lg space-y-1">
              <div class="flex justify-between">
                <span class="text-slate-400">选择器容器:</span>
                <span class="font-mono text-slate-700 truncate max-w-[150px]">{{ cs.rule?.item_selector || '未指定' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">状态记录:</span>
                <span class="font-mono" :class="cs.last_status === 'SUCCESS' ? 'text-emerald-600' : 'text-slate-600'">
                  {{ cs.last_status || '待执行' }}
                </span>
              </div>
            </div>
          </div>

          <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
            <button
              @click="deleteSource(cs.source_key)"
              class="text-rose-500 hover:text-rose-700 text-xs font-semibold transition-colors"
            >
              删除
            </button>
            <div class="flex items-center gap-2">
              <button
                @click="triggerCustomRun(cs.source_key)"
                :disabled="crawlingId === cs.source_key"
                class="px-2.5 py-1 bg-blue-50 hover:bg-blue-100 text-blue-600 font-semibold text-xs rounded transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                <Play class="w-3 h-3" :class="{ 'animate-spin': crawlingId === cs.source_key }" />
                <span>{{ crawlingId === cs.source_key ? '执行中...' : '运行' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Custom Source Drawer Modal -->
    <div v-if="showModal" class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex justify-end">
      <div class="bg-white w-full max-w-xl h-full shadow-2xl flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-200">
        <div class="p-6 space-y-5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                <Sparkles class="w-4 h-4 text-blue-600" />
                新建低代码爬虫数据源
              </h3>
              <p class="text-xs text-slate-500 mt-0.5">配置目标招考网页与提取规则，可在右侧沙箱实时验证</p>
            </div>
            <button @click="showModal = false" class="text-slate-400 hover:text-slate-600 text-xl font-bold">×</button>
          </div>

          <!-- Form Fields -->
          <div class="space-y-4 text-xs">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-semibold text-slate-700 mb-1">爬虫标识 Key</label>
                <input
                  v-model="form.source_key"
                  type="text"
                  placeholder="例如: custom_haikou_cdc"
                  class="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label class="block font-semibold text-slate-700 mb-1">数据源名称</label>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="例如: 海口市疾控中心招考专栏"
                  class="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block font-semibold text-slate-700 mb-1">所属省份</label>
                <input
                  v-model="form.province"
                  type="text"
                  placeholder="例如: 海南"
                  class="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label class="block font-semibold text-slate-700 mb-1">抓取协议</label>
                <select
                  v-model="form.protocol"
                  class="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="html_list">HTML 网页列表 (CSS 选择器)</option>
                  <option value="json_api">前后端分离 JSON API</option>
                  <option value="rss">RSS / XML 订阅源</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block font-semibold text-slate-700 mb-1">目标 URL</label>
              <input
                v-model="form.url"
                type="text"
                placeholder="https://example.com/jobs/list.html"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <!-- Selectors Configuration -->
            <div class="bg-slate-50 p-4 rounded-xl space-y-3 border border-slate-100">
              <h4 class="font-bold text-slate-800 text-[11px] uppercase tracking-wider text-slate-500">字段提取规则 (CSS / JSONPath)</h4>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-slate-600 mb-1">公告列表容器 (Item)</label>
                  <input
                    v-model="form.item_selector"
                    type="text"
                    placeholder="ul.news-list > li"
                    class="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs font-mono focus:outline-none"
                  />
                </div>
                <div>
                  <label class="block text-slate-600 mb-1">公告标题 (Title)</label>
                  <input
                    v-model="form.title_selector"
                    type="text"
                    placeholder="a"
                    class="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs font-mono focus:outline-none"
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-slate-600 mb-1">公告链接 (URL)</label>
                  <input
                    v-model="form.url_selector"
                    type="text"
                    placeholder="a"
                    class="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs font-mono focus:outline-none"
                  />
                </div>
                <div>
                  <label class="block text-slate-600 mb-1">发布日期 (Date)</label>
                  <input
                    v-model="form.date_selector"
                    type="text"
                    placeholder="span.date"
                    class="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs font-mono focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <!-- Sandbox Test Panel -->
            <div class="border border-blue-100 bg-blue-50/50 p-4 rounded-xl space-y-3">
              <div class="flex items-center justify-between">
                <span class="font-bold text-blue-900 text-xs flex items-center gap-1.5">
                  <Zap class="w-3.5 h-3.5 text-blue-600" />
                  实时沙箱联调测试
                </span>
                <button
                  type="button"
                  @click="testSandbox"
                  :disabled="testing"
                  class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded text-[11px] flex items-center gap-1 shadow-sm disabled:opacity-50"
                >
                  <RefreshCw class="w-3 h-3" :class="{ 'animate-spin': testing }" />
                  <span>{{ testing ? '抓取解析中...' : '⚡ 运行测试' }}</span>
                </button>
              </div>

              <!-- Sandbox Results Preview -->
              <div v-if="sandboxResult" class="text-[11px] bg-white p-3 rounded-lg border border-blue-100 space-y-2">
                <div class="flex items-center justify-between text-slate-500 font-mono">
                  <span>抓取状态: <b :class="sandboxResult.status === 'SUCCESS' ? 'text-emerald-600' : 'text-rose-600'">{{ sandboxResult.status }}</b></span>
                  <span>提取条数: {{ sandboxResult.count || 0 }} 条</span>
                </div>
                <div v-if="sandboxResult.error" class="text-rose-600 bg-rose-50 p-2 rounded text-xs">
                  {{ sandboxResult.error }}
                </div>
                <div v-if="sandboxResult.items && sandboxResult.items.length" class="space-y-1.5 pt-1">
                  <div
                    v-for="(item, idx) in sandboxResult.items.slice(0, 3)"
                    :key="idx"
                    class="p-2 bg-slate-50 rounded border border-slate-100 text-xs"
                  >
                    <div class="font-semibold text-slate-800 truncate">{{ item.title }}</div>
                    <div class="text-slate-400 font-mono text-[10px] truncate mt-0.5">{{ item.url }}</div>
                    <div class="text-slate-500 text-[10px] mt-0.5">日期: {{ item.date || '无' }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
          <button
            @click="showModal = false"
            class="px-4 py-2 text-slate-600 hover:text-slate-800 text-xs font-semibold"
          >
            取消
          </button>
          <button
            @click="saveCustomSource"
            :disabled="saving"
            class="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm shadow-blue-500/20 disabled:opacity-50"
          >
            {{ saving ? '保存中...' : '保存并启用' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Globe2, RefreshCw, Sparkles, Plus, Play, Zap } from 'lucide-vue-next'
import {
  fetchSources,
  fetchCustomSources,
  createCustomSource,
  deleteCustomSource,
  testCustomSourceSandbox,
  triggerCustomSourceRun,
  getSchedulerStatus,
  triggerSourceCrawl
} from '@/api'

const activeTab = ref('builtin')
const sources = ref([])
const customSources = ref([])
const schedulerStatus = ref(null)
const crawlingId = ref(null)

const showModal = ref(false)
const testing = ref(false)
const saving = ref(false)
const sandboxResult = ref(null)

const form = reactive({
  source_key: '',
  name: '',
  province: '',
  protocol: 'html_list',
  url: '',
  item_selector: 'ul.news-list > li',
  title_selector: 'a',
  url_selector: 'a',
  date_selector: 'span.date'
})

const loadAllData = async () => {
  try {
    const [srcRes, customRes, schRes] = await Promise.all([
      fetchSources(),
      fetchCustomSources().catch(() => ({ data: [] })),
      getSchedulerStatus()
    ])
    sources.value = srcRes.sources || srcRes || []
    customSources.value = customRes.data || customRes || []
    schedulerStatus.value = schRes
  } catch (err) {
    console.error('Failed to load data:', err)
  }
}

const openCreateModal = () => {
  sandboxResult.value = null
  showModal.value = true
}

const testSandbox = async () => {
  if (!form.url) {
    alert('请先输入目标 URL')
    return
  }
  try {
    testing.value = true
    const payload = {
      protocol: form.protocol,
      url: form.url,
      item_selector: form.item_selector,
      title_selector: form.title_selector,
      url_selector: form.url_selector,
      date_selector: form.date_selector
    }
    const res = await testCustomSourceSandbox(payload)
    sandboxResult.value = res
  } catch (err) {
    sandboxResult.value = { status: 'FAILED', error: err.message }
  } finally {
    testing.value = false
  }
}

const saveCustomSource = async () => {
  if (!form.source_key || !form.name || !form.province || !form.url) {
    alert('请填写完整的基础信息与 URL')
    return
  }
  try {
    saving.value = true
    const payload = {
      source_key: form.source_key,
      name: form.name,
      province: form.province,
      protocol: form.protocol,
      rule: {
        url: form.url,
        item_selector: form.item_selector,
        title_selector: form.title_selector,
        url_selector: form.url_selector,
        date_selector: form.date_selector
      },
      is_active: true
    }
    await createCustomSource(payload)
    showModal.value = false
    await loadAllData()
    alert('自定义爬虫创建并启用成功！')
  } catch (err) {
    alert(`保存失败: ${err.message}`)
  } finally {
    saving.value = false
  }
}

const deleteSource = async (sourceKey) => {
  if (!confirm(`确定删除自定义爬虫 [${sourceKey}] 吗？`)) return
  try {
    await deleteCustomSource(sourceKey)
    await loadAllData()
  } catch (err) {
    alert(`删除失败: ${err.message}`)
  }
}

const triggerCustomRun = async (sourceKey) => {
  try {
    crawlingId.value = sourceKey
    const res = await triggerCustomSourceRun(sourceKey)
    alert(`执行完成！抓取到 ${res.count || 0} 条新数据`)
    await loadAllData()
  } catch (err) {
    alert(`执行失败: ${err.message}`)
  } finally {
    crawlingId.value = null
  }
}

const triggerCrawl = async (sourceId) => {
  try {
    crawlingId.value = sourceId
    const res = await triggerSourceCrawl(sourceId)
    alert(`触发成功！${res.message || '任务已推入执行队列'}`)
    loadAllData()
  } catch (err) {
    alert(`触发失败: ${err.message}`)
  } finally {
    crawlingId.value = null
  }
}

onMounted(() => {
  loadAllData()
})
</script>
