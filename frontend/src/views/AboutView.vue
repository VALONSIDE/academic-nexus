<script setup lang="ts">
import { ArrowLeft, BotMessageSquare, Braces, Database, GraduationCap, Sparkles, UsersRound, WandSparkles } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import LanguageSwitcher from '@/components/LanguageSwitcher.vue'

const { t } = useI18n()
const router = useRouter()

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/login')
}

const capabilities = [
  { key: 'aboutCapabilityPortrait', icon: UsersRound },
  { key: 'aboutCapabilityMatching', icon: WandSparkles },
  { key: 'aboutCapabilityResources', icon: Database },
  { key: 'aboutCapabilityAssistant', icon: BotMessageSquare },
]

const team = [
  { name: '吴磊', role: 'aboutTeamLeadRole', initial: '吴' },
  { name: '刘畅', role: 'aboutTeamDataRole', initial: '刘' },
  { name: '徐前程', role: 'aboutTeamDeveloperRole', initial: '徐' },
]
</script>

<template>
  <main class="min-h-screen bg-slate-100 p-4 text-slate-900 sm:p-6">
    <section class="mx-auto flex min-h-[calc(100vh-2rem)] max-w-7xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/40 sm:min-h-[calc(100vh-3rem)]">
      <header class="flex items-center justify-between border-b border-slate-100 px-5 py-3.5 sm:px-7">
        <button type="button" class="flex items-center gap-2.5 font-semibold tracking-tight" @click="goBack"><span class="grid h-9 w-9 place-items-center rounded-xl bg-slate-950 text-white"><GraduationCap class="h-4 w-4" /></span><span>{{ t('brand') }}</span></button>
        <div class="flex items-center gap-1"><LanguageSwitcher /><button type="button" class="inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900" @click="goBack"><ArrowLeft class="h-4 w-4" />{{ t('returnPreviousPage') }}</button></div>
      </header>

      <div class="grid flex-1 gap-4 p-4 lg:grid-cols-[1.15fr_0.85fr] lg:p-5">
        <article class="rounded-2xl bg-slate-950 p-5 text-white sm:p-6">
          <p class="inline-flex items-center gap-2 rounded-full border border-sky-300/20 bg-sky-300/10 px-3 py-1 text-xs font-medium text-sky-200"><Sparkles class="h-3.5 w-3.5" />{{ t('aboutSubtitle') }}</p>
          <h1 class="mt-4 text-3xl font-semibold tracking-tight">{{ t('aboutTitle') }}</h1>
          <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-300">{{ t('aboutIntroduction') }}</p>
          <div class="mt-5 border-t border-white/10 pt-5"><p class="text-sm font-semibold">{{ t('aboutCapabilities') }}</p><ul class="mt-3 grid gap-2 sm:grid-cols-2"><li v-for="capability in capabilities" :key="capability.key" class="flex gap-2.5 rounded-xl bg-white/7 p-2.5 text-xs leading-5 text-slate-200"><component :is="capability.icon" class="mt-0.5 h-4 w-4 shrink-0 text-sky-300" />{{ t(capability.key) }}</li></ul></div>
        </article>

        <aside class="flex flex-col rounded-2xl border border-slate-200 p-4 sm:p-5">
          <div class="flex items-center gap-2"><UsersRound class="h-5 w-5 text-sky-700" /><h2 class="font-semibold">{{ t('aboutProjectTeam') }}</h2></div>
          <ul class="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-1"><li v-for="member in team" :key="member.name" class="flex items-center gap-3 rounded-xl bg-slate-50 p-2.5"><span class="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-900 text-xs font-semibold text-white">{{ member.initial }}</span><span class="min-w-0"><span class="block text-sm font-medium text-slate-900">{{ member.name }}</span><span class="mt-0.5 block text-xs leading-4 text-slate-500">{{ t(member.role) }}</span></span></li></ul>
          <div class="mt-auto border-t border-slate-100 pt-4"><div class="flex items-center gap-2 text-sm font-semibold"><Braces class="h-4 w-4 text-sky-700" />{{ t('aboutTechnicalDevelopment') }}</div><p class="mt-1 text-sm text-slate-600">{{ t('aboutTechnicalDevelopmentValue') }}</p></div>
        </aside>
      </div>

      <footer class="flex flex-col gap-2 border-t border-slate-100 px-5 py-3 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-7"><span>{{ t('copyrightNotice') }}</span><span class="flex items-center gap-3"><RouterLink to="/legal" class="font-medium text-slate-600 hover:text-slate-900">{{ t('legalCompliance') }}</RouterLink><span>{{ t('aboutCopyrightCompact') }}</span></span></footer>
    </section>
  </main>
</template>
