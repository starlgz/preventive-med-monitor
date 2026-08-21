<template>
  <div class="space-y-6">
    <!-- Stat Cards Overview -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div
        v-for="card in statCards"
        :key="card.title"
        class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm flex items-center justify-between"
      >
        <div>
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">{{ card.title }}</p>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-2xl font-extrabold text-slate-900 tracking-tight font-mono">
              {{ loading ? '...' : card.value }}
            </span>
            <span v-if="card.subtitle" class="text-xs text-slate-400 font-medium">{{ card.subtitle }}</span>
          </div>
        </div>
        <div :class="`w-12 h-12 rounded-xl flex items-center justify-center ${card.bgClass}`">
          <component :is="card.icon" :class="`w-6 h-6 ${card.iconClass}`" />
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Star Distribution (Donut) -->
      <div class="bg-white rounded-xl p-6 border border-slate-200/80 shadow-sm flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
            <Star class="w-4 h-4 text-amber-500" />
            五星专业匹配梯队
          </h3>
          <span class="text-xs text-slate-400">实时分布</span>
        </div>
        <div ref="starChartRef" class="h-64 w-full flex-1"></div>
      </div>

      <!-- Bianzhi Distribution (Pie) -->
      <div class="bg-white rounded-xl p-6 border border-slate-200/80 shadow-sm flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
            <ShieldCheck class="w-4 h-4 text-emerald-600" />
            编制属性研判分布
          </h3>
          <span class="text-xs text-slate-400">证据链判定</span>
        </div>
        <div ref="bianzhiChartRef" class="h-64 w-full flex-1"></div>
      </div>

      <!-- Talent & Policy Tier (Bar) -->
      <div class="bg-white rounded-xl p-6 border border-slate-200/80 shadow-sm flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
            <Award class="w-4 h-4 text-indigo-600" />
            免笔试/人才引进梯队
          </h3>
          <span class="text-xs text-slate-400">政策价值</span>
        </div>
        <div ref="talentChartRef" class="h-64 w-full flex-1"></div>
      </div>
    </div>

    <!-- Province Top Table & Quick Highlights -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Province Top -->
      <div class="bg-white rounded-xl p-6 border border-slate-200/80 shadow-sm">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
            <MapPin class="w-4 h-4 text-blue-600" />
            省份岗位热度 Top 10
          </h3>
          <router-link to="/jobs" class="text-xs text-blue-600 hover:text-blue-700 font-medium">查看全部 &rarr;</router-link>
        </div>
        <div class="space-y-3">
          <div
            v-for="(item, idx) in provinceList"
            :key="item.province"
            class="flex items-center justify-between text-xs"
          >
            <div class="flex items-center gap-2 w-32">
              <span class="w-5 h-5 rounded-full flex items-center justify-center font-bold text-[10px]" :class="idx < 3 ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'">
                {{ idx + 1 }}
              </span>
              <span class="font-medium text-slate-700 truncate">{{ item.province }}</span>
            </div>
            <div class="flex-1 mx-3 bg-slate-100 h-2 rounded-full overflow-hidden">
              <div
                class="bg-blue-500 h-full rounded-full transition-all duration-500"
                :style="{ width: `${Math.min(100, (item.count / maxProvinceCount) * 100)}%` }"
              ></div>
            </div>
            <span class="font-mono font-bold text-slate-700 text-right w-12">{{ item.count }} 岗</span>
          </div>
        </div>
      </div>

      <!-- Core System Highlights -->
      <div class="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-xl p-6 shadow-md flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4">
            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-blue-500/30 text-blue-300 uppercase tracking-wide border border-blue-400/20">
              System Capability
            </span>
            <span class="text-xs text-slate-400 font-mono">100% 全国覆盖</span>
          </div>
          <h4 class="text-lg font-bold text-slate-100 mb-2">预防医学多维高保真研判引擎</h4>
          <p class="text-xs text-slate-300 leading-relaxed mb-4">
            系统深度集成了教育部医学专业目录与疾病预防控制中心实操用人标准，支持对 31 个省市 37 个官方招考源的数据进行 0-Token 本地高精度研判与智能打标。
          </p>
          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="bg-white/5 rounded-lg p-3 border border-white/10">
              <div class="text-slate-400 text-[11px]">五星专业匹配度</div>
              <div class="font-bold text-amber-400 mt-1">5-Star 核心专业</div>
            </div>
            <div class="bg-white/5 rounded-lg p-3 border border-white/10">
              <div class="text-slate-400 text-[11px]">编制证据链模型</div>
              <div class="font-bold text-emerald-400 mt-1">绿标全额 / 黄标存疑</div>
            </div>
          </div>
        </div>

        <div class="mt-6 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
          <span>Telegram 机器人订阅联动</span>
          <router-link to="/bot" class="text-blue-400 hover:text-blue-300 font-medium">配置通道 &rarr;</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import {
  Briefcase,
  ShieldCheck,
  Award,
  TrendingUp,
  Star,
  MapPin
} from 'lucide-vue-next'
import { fetchDashboardStats, fetchDashboardCharts } from '@/api'

const loading = ref(true)
const stats = ref({
  total_jobs: 0,
  five_star_jobs: 0,
  bianzhi_jobs: 0,
  talent_jobs: 0
})
const provinceList = ref([])

const starChartRef = ref(null)
const bianzhiChartRef = ref(null)
const talentChartRef = ref(null)

let starChartInstance = null
let bianzhiChartInstance = null
let talentChartInstance = null

const maxProvinceCount = computed(() => {
  if (!provinceList.value.length) return 1
  return Math.max(...provinceList.value.map(p => p.count), 1)
})

const statCards = computed(() => [
  {
    title: '全网监测岗位总数',
    value: stats.value.total_jobs,
    subtitle: '条数据',
    icon: Briefcase,
    bgClass: 'bg-blue-50',
    iconClass: 'text-blue-600'
  },
  {
    title: '五星/强相关优质岗',
    value: stats.value.five_star_jobs,
    subtitle: '核心对口',
    icon: Star,
    bgClass: 'bg-amber-50',
    iconClass: 'text-amber-500'
  },
  {
    title: '全额事业编制 (绿标)',
    value: stats.value.bianzhi_jobs,
    subtitle: '确定性编制',
    icon: ShieldCheck,
    bgClass: 'bg-emerald-50',
    iconClass: 'text-emerald-600'
  },
  {
    title: '高层次/免笔试引进',
    value: stats.value.talent_jobs,
    subtitle: 'S/A 级通道',
    icon: Award,
    bgClass: 'bg-indigo-50',
    iconClass: 'text-indigo-600'
  }
])

const initCharts = (chartsData) => {
  if (starChartRef.value) {
    starChartInstance = echarts.init(starChartRef.value)
    const starData = chartsData.star_distribution || []
    starChartInstance.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} 岗 ({d}%)' },
      legend: { bottom: '0%', left: 'center', itemWidth: 10, itemHeight: 10, textStyle: { fontSize: 11 } },
      series: [
        {
          name: '星级分布',
          type: 'pie',
          radius: ['45%', '70%'],
          center: ['50%', '42%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          data: starData.map(item => ({
            name: `${item.name}`,
            value: item.value,
            itemStyle: {
              color: item.name.includes('5') ? '#f59e0b' : item.name.includes('4') ? '#3b82f6' : item.name.includes('3') ? '#10b981' : '#94a3b8'
            }
          }))
        }
      ]
    })
  }

  if (bianzhiChartRef.value) {
    bianzhiChartInstance = echarts.init(bianzhiChartRef.value)
    const bData = chartsData.bianzhi_distribution || []
    bianzhiChartInstance.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} 岗 ({d}%)' },
      legend: { bottom: '0%', left: 'center', itemWidth: 10, itemHeight: 10, textStyle: { fontSize: 11 } },
      series: [
        {
          name: '编制属性',
          type: 'pie',
          radius: '65%',
          center: ['50%', '42%'],
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          data: bData.map(item => ({
            name: item.name,
            value: item.value,
            itemStyle: {
              color: item.name.includes('事业') ? '#10b981' : item.name.includes('合同') ? '#ef4444' : '#f59e0b'
            }
          }))
        }
      ]
    })
  }

  if (talentChartRef.value) {
    talentChartInstance = echarts.init(talentChartRef.value)
    const tData = chartsData.talent_distribution || []
    talentChartInstance.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
      xAxis: { type: 'category', data: tData.map(i => i.name), axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value' },
      series: [
        {
          name: '岗位数',
          type: 'bar',
          barWidth: '40%',
          data: tData.map(i => i.value),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#6366f1' },
              { offset: 1, color: '#a855f7' }
            ]),
            borderRadius: [4, 4, 0, 0]
          }
        }
      ]
    })
  }
}

const handleResize = () => {
  starChartInstance?.resize()
  bianzhiChartInstance?.resize()
  talentChartInstance?.resize()
}

onMounted(async () => {
  try {
    loading.value = true
    const [statsRes, chartsRes] = await Promise.all([
      fetchDashboardStats(),
      fetchDashboardCharts()
    ])
    stats.value = statsRes
    provinceList.value = chartsRes.province_distribution || []
    initCharts(chartsRes)
    window.addEventListener('resize', handleResize)
  } catch (err) {
    console.error('Failed to load dashboard data:', err)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  starChartInstance?.dispose()
  bianzhiChartInstance?.dispose()
  talentChartInstance?.dispose()
})
</script>
