<template>
  <div class="min-h-screen flex bg-slate-50 text-slate-800 font-sans">
    <!-- Sidebar -->
    <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0 border-r border-slate-800 shadow-xl select-none">
      <!-- Brand Logo -->
      <div class="h-16 flex items-center px-6 gap-3 bg-slate-950/40 border-b border-slate-800/80">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold text-lg shadow-md shadow-blue-500/20 ring-2 ring-white/10">
          <Activity class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="font-bold text-slate-100 text-sm tracking-wide leading-snug">预防医学招考监测</h1>
          <p class="text-[11px] text-slate-400 font-mono tracking-tighter">PREV-MED OPS v2.0</p>
        </div>
      </div>

      <!-- Nav Links -->
      <nav class="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group"
          :class="[
            $route.path === item.path
              ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-semibold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          ]"
        >
          <component
            :is="item.icon"
            class="w-4 h-4 transition-transform duration-200 group-hover:scale-110"
            :class="[$route.path === item.path ? 'text-white' : 'text-slate-400 group-hover:text-blue-400']"
          />
          <span>{{ item.label }}</span>
          <span
            v-if="item.badge"
            class="ml-auto text-[10px] px-2 py-0.5 rounded-full font-mono font-bold"
            :class="item.badgeClass"
          >
            {{ item.badge }}
          </span>
        </router-link>
      </nav>

      <!-- System Quick Info Footer -->
      <div class="p-4 border-t border-slate-800 bg-slate-950/30 text-xs text-slate-400 space-y-2">
        <div class="flex items-center justify-between">
          <span class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            后台服务状态
          </span>
          <span class="font-mono text-emerald-400 font-medium">HEALTHY</span>
        </div>
        <div class="text-[11px] text-slate-400 flex items-center justify-between">
          <span>全国数据源已覆盖</span>
          <span class="font-mono text-blue-400 font-bold">31 省市 (37 源)</span>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Top Header -->
      <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shadow-sm flex-shrink-0">
        <div class="flex items-center gap-3">
          <h2 class="text-base font-bold text-slate-800">{{ currentRouteTitle }}</h2>
          <span class="text-xs text-slate-400 font-mono hidden md:inline-block">/ {{ currentRoutePath }}</span>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="triggerBatchMatch"
            :disabled="recalculating"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-600 hover:bg-blue-100 hover:text-blue-700 text-xs font-semibold rounded-lg transition-colors border border-blue-200 disabled:opacity-50"
          >
            <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': recalculating }" />
            <span>{{ recalculating ? '正在重算...' : '一键重算五星匹配' }}</span>
          </button>

          <a
            href="/api/v1/dashboard/export/excel"
            target="_blank"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white hover:bg-slate-800 text-xs font-semibold rounded-lg transition-all shadow-sm"
          >
            <Download class="w-3.5 h-3.5" />
            <span>导出优质岗位 (Excel)</span>
          </a>
        </div>
      </header>

      <!-- Router Page Content Container -->
      <main class="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-50/70">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  Activity,
  LayoutDashboard,
  Briefcase,
  Globe2,
  Sliders,
  Send,
  Sparkles,
  RefreshCw,
  Download
} from 'lucide-vue-next'
import { batchMatchAllJobs } from '@/api'

const route = useRoute()
const recalculating = ref(false)

const navItems = [
  { path: '/', label: '数据大盘与态势', icon: LayoutDashboard },
  { path: '/jobs', label: '岗位智选与检索', icon: Briefcase },
  { path: '/sources', label: '数据源与爬虫矩阵', icon: Globe2, badge: '31省市', badgeClass: 'bg-blue-500/20 text-blue-300' },
  { path: '/rules', label: '专业与编制规则引擎', icon: Sliders },
  { path: '/bot', label: 'Telegram 交互中心', icon: Send },
  { path: '/ai-audit', label: 'AI 资格研判复核', icon: Sparkles, badge: '智能', badgeClass: 'bg-purple-500/20 text-purple-300' }
]

const currentRouteTitle = computed(() => route.meta.title || '控制台')
const currentRoutePath = computed(() => route.path.replace('/', '') || 'dashboard')

const triggerBatchMatch = async () => {
  try {
    recalculating.value = true
    const res = await batchMatchAllJobs()
    alert(`重算完成！成功处理: ${res.matched_jobs_count || res.updated_count || '已完成'} 条岗位数据`)
  } catch (err) {
    alert(`重算失败: ${err.message}`)
  } finally {
    recalculating.value = false
  }
}
</script>
