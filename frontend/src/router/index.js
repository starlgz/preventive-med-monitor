import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layout/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: '数据大盘与态势' }
        },
        {
          path: 'jobs',
          name: 'Jobs',
          component: () => import('@/views/JobsView.vue'),
          meta: { title: '岗位智选与检索' }
        },
        {
          path: 'sources',
          name: 'Sources',
          component: () => import('@/views/SourcesView.vue'),
          meta: { title: '数据源与爬虫矩阵' }
        },
        {
          path: 'rules',
          name: 'Rules',
          component: () => import('@/views/RulesView.vue'),
          meta: { title: '专业与编制规则引擎' }
        },
        {
          path: 'bot',
          name: 'Bot',
          component: () => import('@/views/BotView.vue'),
          meta: { title: 'Telegram 推送与交互' }
        },
        {
          path: 'ai-audit',
          name: 'AiAudit',
          component: () => import('@/views/AiAuditView.vue'),
          meta: { title: 'AI 资格研判与复核' }
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 预防医学招考监测系统` : '预防医学招考监测系统'
  next()
})

export default router
