<template>
  <div class="space-y-6">
    <!-- Filter & Search Bar -->
    <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
        <!-- Search -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">关键词搜索</label>
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="岗位名 / 单位 / 专业"
            @keyup.enter="handleSearch"
            class="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
          />
        </div>

        <!-- Province -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">省份地区</label>
          <select
            v-model="filters.province"
            @change="handleSearch"
            class="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
          >
            <option value="">全部省份 (全国)</option>
            <option v-for="p in provinceOptions" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>

        <!-- Star Level -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">专业匹配度</label>
          <select
            v-model="filters.match_level"
            @change="handleSearch"
            class="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
          >
            <option value="">全部星级</option>
            <option :value="5">⭐⭐⭐⭐⭐ 五星核心对口</option>
            <option :value="4">⭐⭐⭐⭐ 四星高度相关</option>
            <option :value="3">⭐⭐⭐ 三星大公共卫生</option>
            <option :value="2">⭐⭐ 二星医学交叉类</option>
            <option :value="1">⭐ 一星宽泛医学类</option>
          </select>
        </div>

        <!-- Bianzhi Type -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">编制判定 (证据链)</label>
          <select
            v-model="filters.bianzhi_type"
            @change="handleSearch"
            class="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
          >
            <option value="">全部类型</option>
            <option value="事业编制">全额/差额事业编 (绿标)</option>
            <option value="存疑待核">存疑待核 (黄标)</option>
            <option value="合同制">合同制/劳务派遣 (红标)</option>
          </select>
        </div>

        <!-- Actions -->
        <div class="flex items-end gap-2">
          <button
            @click="handleSearch"
            class="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold py-2 px-3 rounded-lg transition-colors shadow-sm"
          >
            筛选检索
          </button>
          <button
            @click="resetFilters"
            class="bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-semibold py-2 px-3 rounded-lg transition-colors"
          >
            重置
          </button>
        </div>
      </div>
    </div>

    <!-- Jobs Table List -->
    <div class="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden flex flex-col">
      <div class="px-6 py-4 border-b border-slate-200/80 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <h3 class="font-bold text-slate-800 text-sm">岗位列表</h3>
          <span class="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
            共 {{ total }} 条岗位
          </span>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
              <th class="py-3 px-4">招聘单位 / 岗位名称</th>
              <th class="py-3 px-3">省份/地域</th>
              <th class="py-3 px-3">专业要求 (原始)</th>
              <th class="py-3 px-3">专业匹配度</th>
              <th class="py-3 px-3">编制属性</th>
              <th class="py-3 px-3">避坑/门槛风险</th>
              <th class="py-3 px-3">政策/待遇</th>
              <th class="py-3 px-4 text-right">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="job in jobs"
              :key="job.id"
              class="hover:bg-slate-50/80 transition-colors group cursor-pointer"
              @click="openJobDrawer(job)"
            >
              <!-- Unit & Job Title -->
              <td class="py-3 px-4">
                <div class="font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  {{ job.job_name }}
                </div>
                <div class="text-slate-500 text-[11px] mt-0.5 flex items-center gap-1.5">
                  <span>{{ job.unit_name }}</span>
                  <span v-if="job.unit_type" class="px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 text-[10px]">
                    {{ job.unit_type }}
                  </span>
                </div>
              </td>

              <!-- Province -->
              <td class="py-3 px-3 text-slate-600 font-medium">
                {{ job.province }}
              </td>

              <!-- Major Raw -->
              <td class="py-3 px-3 text-slate-600 max-w-[180px] truncate" :title="job.major_raw">
                {{ job.major_raw || '不限 / 见简章' }}
              </td>

              <!-- Star Rating -->
              <td class="py-3 px-3">
                <div class="flex items-center gap-1">
                  <span class="text-amber-500 font-mono font-bold">{{ '★'.repeat(job.match_level || 0) }}</span>
                  <span class="text-slate-300 font-mono text-[10px]">{{ '★'.repeat(5 - (job.match_level || 0)) }}</span>
                </div>
                <div class="text-[10px] text-slate-400 mt-0.5 truncate max-w-[120px]" :title="job.match_reason">
                  {{ job.match_reason || '常规匹配' }}
                </div>
              </td>

              <!-- Bianzhi Tag -->
              <td class="py-3 px-3">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold"
                  :class="getBianzhiBadgeClass(job.bianzhi_type)"
                >
                  {{ job.bianzhi_type || '未知属性' }}
                </span>
              </td>

              <!-- Pitfall & Risk Level -->
              <td class="py-3 px-3">
                <span
                  v-if="job.pitfall_risk === 'high'"
                  class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200"
                >
                  🔴 高风险锁定
                </span>
                <span
                  v-else-if="job.pitfall_risk === 'medium'"
                  class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200"
                >
                  🟡 提示门槛
                </span>
                <span
                  v-else
                  class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700"
                >
                  🟢 低风险
                </span>
              </td>

              <!-- Policy / Benefits -->
              <td class="py-3 px-3">
                <span
                  v-if="job.talent_tier"
                  class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200/60"
                >
                  {{ job.talent_tier }}
                </span>
                <span v-else class="text-slate-400 text-[11px]">常规统考</span>
              </td>

              <!-- Operations -->
              <td class="py-3 px-4 text-right" @click.stop>
                <div class="flex items-center justify-end gap-2">
                  <button
                    @click="openJobDrawer(job)"
                    class="text-blue-600 hover:text-blue-800 font-semibold text-[11px]"
                  >
                    详情
                  </button>
                  <a
                    v-if="job.announcement_url"
                    :href="job.announcement_url"
                    target="_blank"
                    class="text-slate-400 hover:text-slate-600 text-[11px]"
                  >
                    原文 &nearr;
                  </a>
                </div>
              </td>
            </tr>

            <tr v-if="!loading && jobs.length === 0">
              <td colspan="8" class="py-12 text-center text-slate-400">
                暂无符合条件的招考岗位数据
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Footer -->
      <div class="px-6 py-3 bg-slate-50/50 border-t border-slate-200 flex items-center justify-between text-xs">
        <span class="text-slate-500">
          第 {{ page }} 页，每页 {{ pageSize }} 条
        </span>
        <div class="flex items-center gap-2">
          <button
            :disabled="page <= 1"
            @click="changePage(page - 1)"
            class="px-2.5 py-1 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50 disabled:opacity-40"
          >
            上一页
          </button>
          <button
            :disabled="page * pageSize >= total"
            @click="changePage(page + 1)"
            class="px-2.5 py-1 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50 disabled:opacity-40"
          >
            下一页
          </button>
        </div>
      </div>
    </div>

    <!-- Job Details Drawer Modal -->
    <div
      v-if="selectedJob"
      class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex justify-end transition-opacity"
      @click="selectedJob = null"
    >
      <div
        class="w-full max-w-lg bg-white h-full shadow-2xl p-6 overflow-y-auto space-y-6 flex flex-col justify-between"
        @click.stop
      >
        <div class="space-y-5">
          <!-- Drawer Header -->
          <div class="flex items-start justify-between border-b border-slate-100 pb-4">
            <div>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-600 mb-1 inline-block">
                {{ selectedJob.province }} · {{ selectedJob.unit_type || '事业单位' }}
              </span>
              <h3 class="text-lg font-bold text-slate-900 leading-snug">{{ selectedJob.job_name }}</h3>
              <p class="text-xs text-slate-500 mt-1">{{ selectedJob.unit_name }}</p>
            </div>
            <button
              @click="selectedJob = null"
              class="w-8 h-8 rounded-full bg-slate-100 text-slate-400 hover:text-slate-700 flex items-center justify-center font-bold text-sm"
            >
              ✕
            </button>
          </div>

          <!-- Rating & Bianzhi -->
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-amber-50/60 border border-amber-200/60 rounded-xl p-3">
              <div class="text-[11px] text-amber-700 font-semibold">五星匹配度</div>
              <div class="text-base font-bold text-amber-600 mt-0.5">
                {{ '★'.repeat(selectedJob.match_level || 0) }} ({{ selectedJob.match_level }}星)
              </div>
              <div class="text-[10px] text-amber-600/80 mt-1">{{ selectedJob.match_reason }}</div>
            </div>

            <div class="bg-emerald-50/60 border border-emerald-200/60 rounded-xl p-3">
              <div class="text-[11px] text-emerald-700 font-semibold">编制证据链研判</div>
              <div class="text-base font-bold text-emerald-600 mt-0.5">{{ selectedJob.bianzhi_type }}</div>
              <div class="text-[10px] text-emerald-600/80 mt-1">{{ selectedJob.evidence_chain || '全额事业编制证据充分' }}</div>
            </div>
          </div>

          <!-- Pitfall & Hidden Barriers Alert Box -->
          <div v-if="selectedJob.pitfall_items && selectedJob.pitfall_items.length > 0" class="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2">
            <div class="flex items-center gap-1.5 text-amber-800 font-bold text-xs">
              <span>⚠️ 避坑与隐形门槛预警</span>
              <span class="text-[10px] px-1.5 py-0.2 rounded font-normal bg-amber-200/60">
                服务期/违约/资格条款
              </span>
            </div>
            <ul class="text-xs text-amber-900 list-disc list-inside space-y-1">
              <li v-for="(p, idx) in selectedJob.pitfall_items" :key="idx">
                {{ p }}
              </li>
            </ul>
          </div>

          <!-- Details Grid -->
          <div class="space-y-3 text-xs">
            <div class="bg-slate-50 rounded-lg p-3 space-y-2">
              <div class="flex justify-between">
                <span class="text-slate-400">学历/学位要求:</span>
                <span class="font-semibold text-slate-800">{{ selectedJob.education || '本科及以上' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">年龄限制:</span>
                <span class="font-semibold text-slate-800">{{ selectedJob.age_limit || '35周岁以下' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">招聘人数:</span>
                <span class="font-semibold text-slate-800">{{ selectedJob.recruit_count || 1 }} 人</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">应届生要求:</span>
                <span class="font-semibold text-slate-800">{{ selectedJob.is_fresh_grad ? '仅限应届毕业生' : '不限应届' }}</span>
              </div>
            </div>

            <div>
              <label class="block font-semibold text-slate-700 mb-1">专业目录要求 (原始公告)</label>
              <div class="p-3 bg-slate-50 rounded-lg border border-slate-200/60 text-slate-700 leading-relaxed font-mono">
                {{ selectedJob.major_raw || '无特定专业限制' }}
              </div>
            </div>

            <div v-if="selectedJob.cert_requirements">
              <label class="block font-semibold text-slate-700 mb-1">执业资格与规培证书</label>
              <div class="p-3 bg-slate-50 rounded-lg border border-slate-200/60 text-slate-700">
                {{ selectedJob.cert_requirements }}
              </div>
            </div>

            <div v-if="selectedJob.talent_policy">
              <label class="block font-semibold text-purple-700 mb-1">人才引进与福利政策</label>
              <div class="p-3 bg-purple-50 rounded-lg border border-purple-200/60 text-purple-800">
                {{ selectedJob.talent_policy }}
              </div>
            </div>
          </div>
        </div>

        <!-- Drawer Footer -->
        <div class="pt-4 border-t border-slate-100 flex items-center justify-between gap-3">
          <a
            v-if="selectedJob.announcement_url"
            :href="selectedJob.announcement_url"
            target="_blank"
            class="flex-1 text-center py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg transition-colors shadow-sm"
          >
            打开官方招聘公告原文
          </a>
          <button
            @click="selectedJob = null"
            class="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-lg"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchJobs } from '@/api'

const loading = ref(false)
const jobs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(15)
const selectedJob = ref(null)

const provinceOptions = [
  '北京市', '上海市', '天津市', '重庆市', '广东省', '江苏省', '浙江省', '山东省',
  '河南省', '四川省', '湖北省', '湖南省', '河北省', '安徽省', '福建省', '陕西省',
  '江西省', '辽宁省', '吉林省', '黑龙江省', '内蒙古自治区', '广西壮族自治区',
  '海南省', '贵州省', '云南省', '西藏自治区', '甘肃省', '青海省', '宁夏回族自治区', '新疆维吾尔自治区'
]

const filters = ref({
  keyword: '',
  province: '',
  match_level: '',
  bianzhi_type: ''
})

const getBianzhiBadgeClass = (type) => {
  if (!type) return 'bg-slate-100 text-slate-600'
  if (type.includes('事业')) return 'bg-emerald-50 text-emerald-700 border border-emerald-200'
  if (type.includes('合同') || type.includes('派遣')) return 'bg-rose-50 text-rose-700 border border-rose-200'
  return 'bg-amber-50 text-amber-700 border border-amber-200'
}

const loadJobs = async () => {
  try {
    loading.value = true
    const params = {
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.value.keyword || undefined,
      province: filters.value.province || undefined,
      match_level: filters.value.match_level || undefined,
      bianzhi_type: filters.value.bianzhi_type || undefined
    }
    const res = await fetchJobs(params)
    jobs.value = res.items || res.jobs || []
    total.value = res.total || jobs.value.length
  } catch (err) {
    console.error('Failed to load jobs:', err)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  loadJobs()
}

const resetFilters = () => {
  filters.value = {
    keyword: '',
    province: '',
    match_level: '',
    bianzhi_type: ''
  }
  handleSearch()
}

const changePage = (newPage) => {
  page.value = newPage
  loadJobs()
}

const openJobDrawer = (job) => {
  selectedJob.value = job
}

onMounted(() => {
  loadJobs()
})
</script>
