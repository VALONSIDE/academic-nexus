<script setup lang="ts">
import { computed, ref, type Component } from 'vue'
import { BookOpenCheck, BotMessageSquare, ChevronUp, CircleUserRound, GraduationCap, HardDrive, KeyRound, LayoutDashboard, LogOut, Settings2, SlidersHorizontal, Upload, UserRound, UsersRound, WandSparkles } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import LanguageSwitcher from './LanguageSwitcher.vue'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'

interface NavigationItem {
  label: string
  to: string
  icon: Component
}

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const accountMenuOpen = ref(false)

const activeRole = computed(() => {
  const roles = auth.state.user?.roles || []
  if (roles.includes('admin')) return 'admin'
  if (roles.includes('mentor')) return 'mentor'
  return 'student'
})

const navigation = computed<NavigationItem[]>(() => {
  if (activeRole.value === 'admin') {
    return [
      { label: t('overview'), to: '/admin', icon: LayoutDashboard },
      { label: t('partnerPreRegistration'), to: '/admin/pre-registrations', icon: Upload },
      { label: t('studentManagement'), to: '/admin/students', icon: UsersRound },
      { label: t('mentorManagement'), to: '/admin/mentors', icon: UserRound },
      { label: t('aiQuotaManagement'), to: '/admin/ai-quotas', icon: SlidersHorizontal },
      { label: t('resourceQuotaManagement'), to: '/admin/resource-quotas', icon: HardDrive },
      { label: t('selectionManagement'), to: '/admin/selection', icon: Settings2 },
    ]
  }
  return [
    { label: t('overview'), to: `/${activeRole.value}`, icon: LayoutDashboard },
    { label: t('mentorMatching'), to: `/${activeRole.value}/matches`, icon: WandSparkles },
    { label: activeRole.value === 'student' ? t('learningResources') : t('manageResources'), to: `/${activeRole.value}/resources`, icon: BookOpenCheck },
    { label: t('aiAssistant'), to: `/${activeRole.value}/assistant`, icon: BotMessageSquare },
  ]
})

const homePath = computed(() => `/${activeRole.value}`)
const accountPath = computed(() => `/${activeRole.value}/account`)
const userInitial = computed(() => auth.state.user?.full_name?.trim().slice(0, 1) || '?')

function signOut() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <main class="min-h-screen w-full bg-slate-50 text-slate-900">
    <div class="grid min-h-screen w-full md:grid-cols-[17rem_minmax(0,1fr)]">
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
            <RouterLink v-if="activeRole !== 'admin'" :to="{ path: accountPath, query: { panel: 'portrait' } }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="accountMenuOpen = false"><UserRound class="h-4 w-4" />{{ t('academicPortrait') }}</RouterLink>
            <RouterLink v-if="activeRole !== 'admin'" :to="{ path: accountPath, query: { panel: 'quota' } }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="accountMenuOpen = false"><BotMessageSquare class="h-4 w-4" />{{ t('personalQuota') }}</RouterLink>
          </div>
          <button type="button" class="flex w-full items-center gap-3 rounded-xl p-2.5 text-left transition hover:bg-slate-100" @click="accountMenuOpen = !accountMenuOpen">
            <span class="grid h-9 w-9 place-items-center rounded-full bg-slate-900 text-sm font-semibold text-white">{{ userInitial }}</span>
            <span class="min-w-0 flex-1"><span class="block truncate text-sm font-medium text-slate-800">{{ auth.state.user?.full_name }}</span><span class="block truncate text-xs text-slate-500">{{ t('accountManagement') }}</span></span>
            <ChevronUp class="h-4 w-4 shrink-0 text-slate-500 transition" :class="accountMenuOpen ? '' : 'rotate-180'" />
          </button>
        </div>
      </aside>

      <div class="min-w-0">
        <header class="flex h-[4.5rem] items-center justify-end border-b border-slate-200 bg-white px-6 lg:px-10">
          <div class="flex items-center gap-2">
            <LanguageSwitcher />
            <Button variant="outline" size="sm" type="button" @click="signOut"><LogOut class="mr-1.5 h-3.5 w-3.5" />{{ t('logout') }}</Button>
          </div>
        </header>
        <section class="w-full px-6 py-8 sm:px-8 lg:px-10 lg:py-10 2xl:px-14"><slot /></section>
      </div>
    </div>
  </main>
</template>
