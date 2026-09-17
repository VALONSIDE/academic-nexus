<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import { ArrowUpRight, BellRing, BookOpenCheck, BotMessageSquare, ChartNoAxesCombined, CheckCircle2, ChevronRight, Clock3, Database, GraduationCap, HardDrive, Sparkles, UsersRound, WandSparkles } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import ResourceRecommendationPanel from '@/components/ResourceRecommendationPanel.vue'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { DashboardBreakdown, DashboardMetric, DashboardOverview, Role } from '@/types/auth'

const { t } = useI18n()
const auth = useAuthStore()
const route = useRoute()
const activeRole = computed<Role>(() => {
  const roles = auth.state.user?.roles || []
  const routeRole = route.path.split('/')[1]
  if ((routeRole === 'student' || routeRole === 'mentor') && roles.includes(routeRole)) return routeRole
  return roles.some(role => ['admin', 'super_admin', 'institution_admin'].includes(role)) ? 'admin' : roles.includes('mentor') ? 'mentor' : 'student'
})
const data = ref<DashboardOverview | null>(null)
const loading = ref(false)
const error = ref('')

const metricLabels: Record<string, string> = {
  students_total: 'studentsTotal', mentors_total: 'mentorsTotal', preregistrations_pending: 'preregistrationsPending', resources_total: 'resourcesTotal', ai_project_calls: 'aiProjectCalls', mentor_matches_available: 'mentorMatchesAvailable', student_candidates_available: 'studentCandidatesAvailable', resources_owned: 'resourcesOwned', resource_storage: 'resourceStorage', ai_cycle_credits: 'aiCycleCredits', ai_credit_balance: 'dashboardAiCreditBalance',
}
const metricIcons: Record<string, Component> = {
  students_total: UsersRound, mentors_total: GraduationCap, preregistrations_pending: Database, resources_total: BookOpenCheck, ai_project_calls: BotMessageSquare, mentor_matches_available: Sparkles, student_candidates_available: UsersRound, resources_owned: BookOpenCheck, resource_storage: HardDrive, ai_cycle_credits: BotMessageSquare, ai_credit_balance: Sparkles,
}
const selectionLabels: Record<string, string> = { pending_student: 'selectedPending', pending_mentor: 'mentorInvitationPending', confirmed: 'selectionConfirmed', rejected: 'rejected', cancelled: 'cancelled' }
const selectionMax = computed(() => Math.max(1, ...(data.value?.selection_statistics.map((item) => item.value) || [1])))
const roleLabel = computed(() => t(`${activeRole.value}Dashboard`))
const displayName = computed(() => auth.state.user?.full_name || auth.state.user?.username || '')

const quickActions = computed<{ label: string; description?: string; to: string; icon: Component }[]>(() => {
  if (activeRole.value === 'admin') {
    const isSuperAdmin = auth.state.user?.roles.some(role => ['admin', 'super_admin'].includes(role))
    return [
      ...(isSuperAdmin ? [{ label: t('partnerPreRegistration'), description: t('dashboardActionAdministrationDescription'), to: '/admin/pre-registrations', icon: Database }] : []),
      { label: t('studentManagement'), description: t('institutionUserManagementDescription'), to: '/admin/students', icon: UsersRound },
      { label: t('subscriptionManagement'), description: t('subscriptionManagementShortDescription'), to: '/admin/subscriptions', icon: BotMessageSquare },
      ...(isSuperAdmin ? [{ label: t('selectionManagement'), description: t('dashboardActionMatchesDescription'), to: '/admin/selection', icon: ChartNoAxesCombined }] : []),
    ]
  }
  return [
    { label: activeRole.value === 'mentor' ? t('studentMatching') : t('mentorMatching'), description: t('dashboardActionMatchesDescription'), to: `/${activeRole.value}/matches`, icon: WandSparkles },
    { label: activeRole.value === 'student' ? t('learningResources') : t('manageResources'), description: t('dashboardActionResourcesDescription'), to: `/${activeRole.value}/resources`, icon: BookOpenCheck },
    { label: t('aiAssistant'), to: `/${activeRole.value}/assistant`, icon: BotMessageSquare },
  ]
})

function displayMetric(metric: DashboardMetric) {
  if (metric.code === 'resource_storage') return `${(metric.value / 1024 / 1024).toFixed(1)} MB`
  return metric.total !== null ? `${metric.value}/${metric.total}` : String(metric.value)
}

function metricProgress(metric: DashboardMetric) {
  if (!metric.total) return 0
  return Math.min(100, Math.round(metric.value / metric.total * 100))
}

function width(item: DashboardBreakdown) {
  return `${Math.max(item.value ? 8 : 0, item.value / selectionMax.value * 100)}%`
}

function activityText(item: DashboardOverview['recent_selection_activity'][number]) {
  return `${item.student_name} · ${item.mentor_name}`
}

function activityStatus(status: string) {
  return t(selectionLabels[status] || status)
}

async function load() {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  try {
    data.value = await authApi.dashboard(auth.state.token)
  } catch {
    error.value = t('updateFailed')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <DashboardLayout>
    <div class="mx-auto w-full max-w-[96rem]">
      <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div class="flex flex-col gap-5 p-6 sm:p-7 lg:flex-row lg:items-end lg:justify-between">
          <div><div class="flex items-center gap-2 text-sm text-slate-500"><span class="grid h-7 w-7 place-items-center rounded-lg bg-sky-50 text-sky-700"><ChartNoAxesCombined class="h-4 w-4" /></span>{{ roleLabel }}</div><h1 class="mt-4 text-3xl font-semibold tracking-tight text-slate-950">{{ t('dashboardWelcome', { name: displayName }) }}</h1><p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{{ t('dashboardSubtitle') }}</p></div>
          <RouterLink :to="quickActions[0]?.to || '/login'" class="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"><Sparkles class="h-4 w-4" />{{ t('openWorkspace') }}<ArrowUpRight class="h-4 w-4" /></RouterLink>
        </div>
        <div class="border-t border-slate-100 bg-slate-50/70 px-6 py-3 text-xs text-slate-500 sm:px-7"><span class="font-medium text-slate-700">{{ auth.state.user?.username }}</span><span class="mx-2 text-slate-300">/</span>{{ t('dashboardMetrics') }}</div>
      </section>

      <div v-if="loading" class="py-20 text-center text-sm text-slate-500">{{ t('loading') }}</div>
      <template v-else-if="data">
        <section class="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-5"><Card v-for="metric in data.metrics" :key="metric.code" class="group min-w-0 rounded-xl p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"><div class="flex items-start justify-between gap-3"><p class="text-sm leading-5 text-slate-500">{{ t(metricLabels[metric.code] || metric.code) }}</p><span class="grid h-8 w-8 place-items-center rounded-lg bg-slate-100 text-slate-600 transition group-hover:bg-sky-50 group-hover:text-sky-700"><component :is="metricIcons[metric.code] || Sparkles" class="h-4 w-4" /></span></div><p class="mt-5 truncate text-2xl font-semibold tracking-tight text-slate-950">{{ displayMetric(metric) }}</p><div v-if="metric.total !== null" class="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full bg-gradient-to-r from-sky-500 to-indigo-500" :style="{ width: `${metricProgress(metric)}%` }" /></div></Card></section>

        <section class="mt-6 grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
          <Card class="rounded-2xl p-6 shadow-sm"><div class="flex items-center justify-between gap-3"><div><div class="flex items-center gap-2"><span class="grid h-8 w-8 place-items-center rounded-lg bg-sky-50 text-sky-700"><CheckCircle2 class="h-4 w-4" /></span><h2 class="font-semibold text-slate-900">{{ t('selectionStatistics') }}</h2></div><p class="mt-2 text-sm text-slate-500">{{ t('selectionIntro') }}</p></div><ChartNoAxesCombined class="h-5 w-5 shrink-0 text-slate-400" /></div><div v-if="data.selection_statistics.length" class="mt-7 space-y-5"><div v-for="item in data.selection_statistics" :key="item.code"><div class="mb-2 flex items-center justify-between gap-4 text-sm"><span class="text-slate-600">{{ t(selectionLabels[item.code] || item.code) }}</span><span class="font-semibold text-slate-900">{{ item.value }}</span></div><div class="h-2 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full bg-slate-900 transition-all" :style="{ width: width(item) }" /></div></div></div><div v-else class="mt-7 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">{{ t('selectionActivityEmpty') }}</div></Card>

          <Card class="rounded-2xl p-6 shadow-sm"><div class="flex items-center justify-between gap-3"><div class="flex items-center gap-2"><span class="grid h-8 w-8 place-items-center rounded-lg bg-violet-50 text-violet-700"><BellRing class="h-4 w-4" /></span><h2 class="font-semibold text-slate-900">{{ t('latestSelectionMessages') }}</h2></div><Clock3 class="h-5 w-5 text-slate-400" /></div><div v-if="data.recent_selection_activity.length" class="mt-5 divide-y divide-slate-100"><div v-for="item in data.recent_selection_activity" :key="item.id" class="flex items-center gap-3 py-3.5"><span class="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">{{ item.student_name.slice(0, 1) }}</span><div class="min-w-0 flex-1"><p class="truncate text-sm font-medium text-slate-800">{{ activityText(item) }}</p><p class="mt-1 text-xs text-slate-500">{{ activityStatus(item.status) }}</p></div><ChevronRight class="h-4 w-4 shrink-0 text-slate-300" /></div></div><div v-else class="mt-7 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">{{ t('selectionActivityEmpty') }}</div></Card>
        </section>

        <section class="mt-6"><div class="mb-4 flex items-center justify-between"><div><h2 class="text-lg font-semibold text-slate-900">{{ t('quickActions') }}</h2><p class="mt-1 text-sm text-slate-500">{{ roleLabel }}</p></div></div><div class="grid gap-4 md:grid-cols-3"><RouterLink v-for="action in quickActions" :key="action.to" :to="action.to" class="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md"><span class="grid h-10 w-10 place-items-center rounded-xl bg-slate-100 text-slate-700 transition group-hover:bg-slate-950 group-hover:text-white"><component :is="action.icon" class="h-5 w-5" /></span><div class="mt-5 flex items-start justify-between gap-3"><div><h3 class="font-semibold text-slate-900">{{ action.label }}</h3><p v-if="action.description" class="mt-1.5 text-sm leading-6 text-slate-600">{{ action.description }}</p></div><ArrowUpRight class="h-4 w-4 shrink-0 text-slate-400 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-slate-900" /></div></RouterLink></div></section>
        <ResourceRecommendationPanel v-if="activeRole === 'student'" />
      </template>
      <p v-else-if="error" class="mt-8 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
    </div>
  </DashboardLayout>
</template>
