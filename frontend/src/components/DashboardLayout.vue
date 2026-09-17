<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import { BookOpenCheck, BotMessageSquare, Building2, ChevronUp, CircleUserRound, CreditCard, FileKey2, GraduationCap, HardDrive, KeyRound, LayoutDashboard, LogOut, Settings2, ShieldCheck, Upload, UserRound, UsersRound, WandSparkles } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import LanguageSwitcher from './LanguageSwitcher.vue'
import { authApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'

interface NavigationItem {
  label: string
  to: string
  icon: Component
}

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const accountMenuOpen = ref(false)
const subscriptionPlan = ref<'basic' | 'pro' | 'ultra' | 'max'>('basic')
const institutionAdminName = ref('')

const isSuperAdmin = computed(() => {
  const roles = auth.state.user?.roles || []
  return roles.includes('admin') || roles.includes('super_admin')
})

const isInstitutionAdmin = computed(() => auth.state.user?.roles.includes('institution_admin') || false)

const isAdministrator = computed(() => isSuperAdmin.value || isInstitutionAdmin.value)

const activeRole = computed(() => {
  const roles = auth.state.user?.roles || []
  const routeRole = route.path.split('/')[1]
  if ((routeRole === 'student' || routeRole === 'mentor') && roles.includes(routeRole)) return routeRole
  if (isAdministrator.value) return 'admin'
  if (roles.includes('mentor')) return 'mentor'
  return 'student'
})

const academicRole = computed<'student' | 'mentor' | null>(() => {
  const roles = auth.state.user?.roles || []
  if (roles.includes('mentor')) return 'mentor'
  if (roles.includes('student')) return 'student'
  return null
})

const hasAcademicPortrait = computed(() => academicRole.value !== null)

const navigation = computed<NavigationItem[]>(() => {
  if (activeRole.value === 'admin') {
    const items = [
      { label: t('overview'), to: '/admin', icon: LayoutDashboard },
      { label: t('studentManagement'), to: '/admin/students', icon: UsersRound },
      { label: t('mentorManagement'), to: '/admin/mentors', icon: UserRound },
      { label: t('subscriptionManagement'), to: '/admin/subscriptions', icon: CreditCard },
      { label: t('subscriptionDelivery'), to: '/admin/subscription-delivery', icon: FileKey2 },
    ]
    if (isSuperAdmin.value) {
      items.splice(1, 0, { label: t('partnerPreRegistration'), to: '/admin/pre-registrations', icon: Upload })
      items.splice(2, 0, { label: t('institutionManagement'), to: '/admin/institutions', icon: Building2 })
      items.push(
        { label: t('resourceQuotaManagement'), to: '/admin/resource-quotas', icon: HardDrive },
        { label: t('selectionManagement'), to: '/admin/selection', icon: Settings2 },
      )
    }
    return items
  }
  return [
    { label: t('overview'), to: `/${activeRole.value}`, icon: LayoutDashboard },
    { label: activeRole.value === 'mentor' ? t('studentMatching') : t('mentorMatching'), to: `/${activeRole.value}/matches`, icon: WandSparkles },
    { label: activeRole.value === 'student' ? t('learningResources') : t('manageResources'), to: `/${activeRole.value}/resources`, icon: BookOpenCheck },
    { label: t('aiAssistant'), to: `/${activeRole.value}/assistant`, icon: BotMessageSquare },
  ]
})

const homePath = computed(() => `/${activeRole.value}`)
const accountPath = computed(() => `/${activeRole.value}/account`)
const userInitial = computed(() => auth.state.user?.full_name?.trim().slice(0, 1) || '?')
const accountIdentityLabel = computed(() => {
  if (isSuperAdmin.value) return t('superAdministrator')
  if (isInstitutionAdmin.value) return institutionAdminName.value ? `${institutionAdminName.value} ${t('administratorSuffix')}` : t('institutionAdministrator')
  if (subscriptionPlan.value === 'basic') return t('standardAccount')
  return t({ pro: 'subscriptionPlanPro', ultra: 'subscriptionPlanUltra', max: 'subscriptionPlanMax' }[subscriptionPlan.value])
})

async function loadAccountIdentity() {
  if (!auth.state.token) return
  try {
    if (isInstitutionAdmin.value && !isSuperAdmin.value) {
      const scopes = await authApi.myInstitutionAdminScopes(auth.state.token)
      institutionAdminName.value = scopes[0]?.institution_name_zh || ''
    } else if (!isAdministrator.value) {
      subscriptionPlan.value = (await authApi.subscription(auth.state.token)).plan_code
    }
  } catch {
    // Keep the safe fallback label if the optional metadata lookup fails.
  }
}

function signOut() {
  auth.logout()
  router.push('/login')
}

onMounted(loadAccountIdentity)
</script>

<template>
  <main class="min-h-screen w-full bg-slate-50 text-slate-900 md:h-dvh md:overflow-hidden">
    <div class="grid min-h-screen w-full md:h-full md:grid-cols-[17rem_minmax(0,1fr)]">
      <aside class="flex border-b border-slate-200 bg-white md:sticky md:top-0 md:h-screen md:flex-col md:border-r md:border-b-0">
        <div class="flex min-h-[4.5rem] items-center border-b border-slate-100 px-6 md:pt-1">
          <RouterLink :to="homePath" class="flex items-center gap-2 font-semibold tracking-tight">
            <span class="grid h-8 w-8 place-items-center rounded-lg bg-slate-900 text-white"><GraduationCap class="h-4 w-4" /></span>
            <span>{{ t('brand') }}</span>
          </RouterLink>
        </div>
        <nav class="flex flex-1 items-center gap-1 overflow-x-auto px-4 py-2 md:flex-col md:items-stretch md:px-4 md:py-6" :aria-label="t('workspace')">
          <RouterLink
            v-for="item in navigation"
            :key="item.to"
            :to="item.to"
            class="flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 md:shrink"
            active-class="bg-slate-900 text-white shadow-sm hover:bg-slate-900 hover:text-white"
          >
            <component :is="item.icon" class="h-4 w-4 shrink-0" /><span class="whitespace-nowrap">{{ item.label }}</span>
          </RouterLink>
        </nav>
        <div class="relative hidden border-t border-slate-100 p-4 md:block">
          <div v-if="accountMenuOpen" class="absolute bottom-[calc(100%+.5rem)] left-4 right-4 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
            <RouterLink :to="accountPath" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="accountMenuOpen = false"><CircleUserRound class="h-4 w-4" />{{ t('accountManagement') }}</RouterLink>
            <RouterLink :to="{ path: accountPath, query: { panel: 'password' } }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="accountMenuOpen = false"><KeyRound class="h-4 w-4" />{{ t('changePassword') }}</RouterLink>
            <RouterLink v-if="hasAcademicPortrait" :to="{ path: accountPath, query: { panel: 'portrait' } }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="accountMenuOpen = false"><UserRound class="h-4 w-4" />{{ t('academicPortrait') }}</RouterLink>
            <RouterLink v-if="activeRole !== 'admin'" :to="`/${activeRole}/subscription`" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="accountMenuOpen = false"><CreditCard class="h-4 w-4" />{{ t('subscription') }}</RouterLink>
            <RouterLink to="/legal" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="accountMenuOpen = false"><ShieldCheck class="h-4 w-4" />{{ t('legalCompliance') }}</RouterLink>
          </div>
          <button type="button" class="flex w-full items-center gap-3 rounded-xl p-2.5 text-left transition hover:bg-slate-100" @click="accountMenuOpen = !accountMenuOpen">
            <span class="grid h-9 w-9 place-items-center rounded-full bg-slate-900 text-sm font-semibold text-white">{{ userInitial }}</span>
            <span class="min-w-0 flex-1"><span class="block truncate text-sm font-medium text-slate-800">{{ auth.state.user?.full_name }}</span><span class="block truncate text-xs text-slate-500">{{ accountIdentityLabel }}</span></span>
            <ChevronUp class="h-4 w-4 shrink-0 text-slate-500 transition" :class="accountMenuOpen ? '' : 'rotate-180'" />
          </button>
        </div>
      </aside>

      <div class="min-w-0 md:flex md:h-full md:min-h-0 md:flex-col">
        <header class="flex h-[4.5rem] shrink-0 items-center justify-end border-b border-slate-200 bg-white px-6 lg:px-10">
          <div class="flex items-center gap-2">
            <RouterLink to="/about" class="rounded-md px-2 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900">{{ t('about') }}</RouterLink>
            <LanguageSwitcher />
            <Button variant="outline" size="sm" type="button" @click="signOut"><LogOut class="mr-1.5 h-3.5 w-3.5" />{{ t('logout') }}</Button>
          </div>
        </header>
        <section class="w-full px-6 py-8 sm:px-8 lg:px-10 lg:py-10 2xl:px-14 md:min-h-0 md:flex-1 md:overflow-y-auto"><slot /></section>
      </div>
    </div>
  </main>
</template>
