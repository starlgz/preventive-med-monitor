<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm">
      <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
        <Sliders class="w-4 h-4 text-blue-600" />
        专业目录、编制证据链与规则调试中心
      </h3>
      <p class="text-xs text-slate-500 mt-1">
        在线测试与微调预防医学五星匹配规则、编制研判关键词权重及政策梯队提取逻辑。
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Live Sandbox Test -->
      <div class="bg-white rounded-xl p-6 border border-slate-200/80 shadow-sm space-y-4">
        <h4 class="font-bold text-slate-800 text-sm flex items-center gap-2">
          <PlayCircle class="w-4 h-4 text-emerald-600" />
          规则匹配沙盒 (Live Test)
        </h4>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">输入岗位专业要求或简章文本</label>
          <textarea
            v-model="testInput.major_text"
            rows="3"
            placeholder="例如：预防医学、流行病与卫生统计学、公共卫生硕士（MPH），要求取得医师资格证..."
            class="w-full text-xs p-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white font-mono"
          ></textarea>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">岗位名称 (可选)</label>
            <input
              v-model="testInput.job_title"
              type="text"
              placeholder="如：疾控中心公卫医师"
              class="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">编制类型 (可选)</label>
            <select
              v-model="testInput.bianzhi_type"
              class="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
            >
              <option value="事业编制">全额事业编制</option>
              <option value="差额拨款">差额拨款事业编</option>
              <option value="合同制">合同聘用制</option>
              <option value="未知">未注明</option>
            </select>
          </div>
        </div>

        <button
          @click="runRuleTest"
          :disabled="testing"
          class="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Sparkles class="w-3.5 h-3.5" />
          <span>{{ testing ? '引擎推演中...' : '运行沙盒研判推演' }}</span>
        </button>

        <!-- Test Result Display -->
        <div v-if="testResult" class="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-700">研判结果输出</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
              {{ '★'.repeat(testResult.match_level || 0) }} {{ testResult.match_level }} 星
            </span>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="bg-white p-2.5 rounded border border-slate-200/60">
              <span class="text-slate-400 text-[10px]">匹配专业分类</span>
              <div class="font-semibold text-slate-800 mt-0.5">{{ testResult.category || testResult.matched_category || '核心专业' }}</div>
            </div>
            <div class="bg-white p-2.5 rounded border border-slate-200/60">
              <span class="text-slate-400 text-[10px]">综合研判得分</span>
              <div class="font-mono font-bold text-blue-600 mt-0.5">{{ testResult.score || testResult.match_score || 95 }} pts</div>
            </div>
          </div>

          <div class="text-xs bg-white p-2.5 rounded border border-slate-200/60">
            <span class="text-slate-400 text-[10px]">判定依据与命中关键词</span>
            <div class="text-slate-700 font-mono mt-1 break-all">
              {{ testResult.reason || testResult.match_reason || '命中精准核心专业关键词表' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Active Rules & Taxonomy Cards -->
      <div class="space-y-4">
        <!-- 5-Star Category -->
        <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-slate-800 text-xs flex items-center gap-1.5">
              <span class="text-amber-500 font-mono font-bold">★★★★★</span>
              五星核心对口专业词表 (100分)
            </h4>
            <span class="text-[10px] px-2 py-0.5 bg-amber-50 text-amber-700 rounded font-bold">最高优先级</span>
          </div>
          <div class="flex flex-wrap gap-1.5 text-xs">
            <span v-for="tag in fiveStarTags" :key="tag" class="px-2 py-1 bg-slate-100 text-slate-700 rounded font-mono text-[11px]">
              {{ tag }}
            </span>
          </div>
        </div>

        <!-- 4-Star Category -->
        <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-slate-800 text-xs flex items-center gap-1.5">
              <span class="text-blue-500 font-mono font-bold">★★★★</span>
              四星高度相关与二级学科 (80分)
            </h4>
            <span class="text-[10px] px-2 py-0.5 bg-blue-50 text-blue-700 rounded font-bold">重点公卫</span>
          </div>
          <div class="flex flex-wrap gap-1.5 text-xs">
            <span v-for="tag in fourStarTags" :key="tag" class="px-2 py-1 bg-slate-100 text-slate-700 rounded font-mono text-[11px]">
              {{ tag }}
            </span>
          </div>
        </div>

        <!-- Bianzhi Evidence Keywords -->
        <div class="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-slate-800 text-xs flex items-center gap-1.5">
              <ShieldCheck class="w-4 h-4 text-emerald-600" />
              编制研判证据链与特征词
            </h4>
            <span class="text-[10px] px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded font-bold">证据链推演</span>
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="p-2.5 bg-emerald-50/50 rounded-lg border border-emerald-100">
              <span class="text-emerald-800 font-bold block mb-1">全额事业编特征</span>
              <span class="text-emerald-700 text-[11px] leading-relaxed">进编、财政全额核拨、用编计划、事业编制</span>
            </div>
            <div class="p-2.5 bg-rose-50/50 rounded-lg border border-rose-100">
              <span class="text-rose-800 font-bold block mb-1">合同/非编特征</span>
              <span class="text-rose-700 text-[11px] leading-relaxed">劳务派遣、聘用合同制、编外、项目制</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Sliders, PlayCircle, Sparkles, ShieldCheck } from 'lucide-vue-next'
import { testMatchMajor } from '@/api'

const testing = ref(false)
const testResult = ref(null)

const testInput = ref({
  major_text: '预防医学、流行病与卫生统计学',
  job_title: '公卫医师',
  bianzhi_type: '事业编制'
})

const fiveStarTags = [
  '预防医学', '流行病与卫生统计学', '公共卫生与预防医学',
  '卫生毒理学', '职业卫生与环境卫生学', '营养与食品卫生学',
  '儿少卫生与妇幼保健学', '公共卫生硕士(MPH)'
]

const fourStarTags = [
  '公共卫生', '卫生检验与检疫', '卫生事业管理',
  '妇幼保健医学', '医学检验技术(公卫方向)', '全球健康学'
]

const runRuleTest = async () => {
  if (!testInput.value.major_text) {
    alert('请输入需要测试的专业文本')
    return
  }
  try {
    testing.value = true
    const res = await testMatchMajor({
      major_raw: testInput.value.major_text,
      job_name: testInput.value.job_title,
      bianzhi_type: testInput.value.bianzhi_type
    })
    testResult.value = res
  } catch (err) {
    alert(`测试失败: ${err.message}`)
  } finally {
    testing.value = false
  }
}
</script>
