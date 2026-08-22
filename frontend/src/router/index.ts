import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/types/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login/:role?', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/activate', name: 'activate', component: () => import('@/views/ActivateView.vue') },
    { path: '/activate/profile', name: 'activation-profile', component: () => import('@/views/ActivationProfileView.vue') },
    { path: '/registration-complete', name: 'registration-complete', component: () => import('@/views/RegistrationCompleteView.vue'), meta: { requiresAuth: true } },
    { path: '/register/:pathMatch(.*)*', redirect: '/activate' },
    { path: '/admin/pre-registrations', name: 'admin-pre-registrations', component: () => import('@/views/PreRegistrationAdminView.vue'), meta: { role: 'admin' } },
    { path: '/admin/students', name: 'admin-students', component: () => import('@/views/UserManagementView.vue'), props: { role: 'student' }, meta: { role: 'admin' } },
    { path: '/admin/mentors', name: 'admin-mentors', component: () => import('@/views/UserManagementView.vue'), props: { role: 'mentor' }, meta: { role: 'admin' } },
    { path: '/admin/ai-quotas', name: 'admin-ai-quotas', component: () => import('@/views/AdminAiQuotaView.vue'), meta: { role: 'admin' } },
    { path: '/admin/resource-quotas', name: 'admin-resource-quotas', component: () => import('@/views/AdminResourceQuotaView.vue'), meta: { role: 'admin' } },
    { path: '/admin/selection', name: 'admin-selection', component: () => import('@/views/AdminSelectionView.vue'), meta: { role: 'admin' } },
    { path: '/admin/account', name: 'admin-account', component: () => import('@/views/AccountManagementView.vue'), meta: { role: 'admin' } },
    { path: '/student', name: 'student-dashboard', component: () => import('@/views/DashboardView.vue'), meta: { role: 'student' } },
    { path: '/student/profile', redirect: { path: '/student/account', query: { panel: 'portrait' } } },
    { path: '/student/matches', name: 'student-matches', component: () => import('@/views/MentorMatchingView.vue'), meta: { role: 'student' } },
    { path: '/student/resources', name: 'student-resources', component: () => import('@/views/ResourceLibraryView.vue'), meta: { role: 'student' } },
    { path: '/student/assistant', name: 'student-ai-assistant', component: () => import('@/views/AiAssistantView.vue'), meta: { role: 'student' } },
    { path: '/student/account', name: 'student-account', component: () => import('@/views/AccountManagementView.vue'), meta: { role: 'student' } },
    { path: '/mentor', name: 'mentor-dashboard', component: () => import('@/views/DashboardView.vue'), meta: { role: 'mentor' } },
    { path: '/mentor/profile', redirect: { path: '/mentor/account', query: { panel: 'portrait' } } },
    { path: '/mentor/matches', name: 'mentor-matches', component: () => import('@/views/MentorMatchingView.vue'), meta: { role: 'mentor' } },
    { path: '/mentor/resources', name: 'mentor-resources', component: () => import('@/views/MentorResourcesView.vue'), meta: { role: 'mentor' } },
    { path: '/mentor/assistant', name: 'mentor-ai-assistant', component: () => import('@/views/AiAssistantView.vue'), meta: { role: 'mentor' } },
    { path: '/mentor/account', name: 'mentor-account', component: () => import('@/views/AccountManagementView.vue'), meta: { role: 'mentor' } },
    { path: '/admin', name: 'admin-dashboard', component: () => import('@/views/DashboardView.vue'), meta: { role: 'admin' } },
  ],
})

router.beforeEach(async (to) => {
  const expectedRole = to.meta.role as Role | undefined
  const auth = useAuthStore()
  const requiresAuth = Boolean(to.meta.requiresAuth) || Boolean(expectedRole)
  if (!requiresAuth) return true
  if (!auth.state.user && auth.state.token) await auth.refreshUser()
  if (!auth.state.user) return { name: 'login', params: expectedRole ? { role: expectedRole } : {} }
  if (!expectedRole) return true
  if (!auth.state.user.roles.includes(expectedRole)) return { name: 'login', params: { role: expectedRole } }
  return true
})

export default router
