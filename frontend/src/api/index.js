import apiClient from './client'

export const fetchDashboardStats = () => apiClient.get('/dashboard/stats')
export const fetchDashboardCharts = () => apiClient.get('/dashboard/charts')

export const fetchJobs = (params) => apiClient.get('/dashboard/jobs', { params })
export const fetchJobDetail = (id) => apiClient.get(`/dashboard/jobs/${id}`)

export const fetchSources = () => apiClient.get('/sources')
export const getSchedulerStatus = () => apiClient.get('/sources/scheduler/status')
export const triggerSourceCrawl = (sourceId) => apiClient.post(`/sources/${sourceId}/trigger`)

export const testMatchMajor = (data) => apiClient.post('/rules/match_major', data)
export const batchMatchAllJobs = () => apiClient.post('/rules/batch_match_all_jobs')

export const testBotCommand = (data) => apiClient.post('/bot/command', data)
export const evaluateJobAI = (data) => apiClient.post('/ai/evaluate_job', data)

// 自定义低代码爬虫接口
export const fetchCustomSources = () => apiClient.get('/sources/custom')
export const createCustomSource = (data) => apiClient.post('/sources/custom', data)
export const updateCustomSource = (sourceKey, data) => apiClient.put(`/sources/custom/${sourceKey}`, data)
export const deleteCustomSource = (sourceKey) => apiClient.delete(`/sources/custom/${sourceKey}`)
export const testCustomSourceSandbox = (data) => apiClient.post('/sources/custom/test', data)
export const triggerCustomSourceRun = (sourceKey) => apiClient.post(`/sources/custom/${sourceKey}/run`)

export const fetchSystemHealth = () => apiClient.get('/health')
