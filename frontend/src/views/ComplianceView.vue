<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, BookOpenText, BrainCircuit, ChevronRight, LockKeyhole, Scale, ShieldCheck } from 'lucide-vue-next'

import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import { legalDocument, legalDocuments, type LegalDocumentId } from '@/content/legal'
import type { Locale } from '@/types/auth'

const route = useRoute()
const router = useRouter()
const { locale, t } = useI18n()
const currentLocale = computed(() => locale.value as Locale)
const documentId = computed(() => route.params.document as string | undefined)
const document = computed(() => legalDocument(currentLocale.value, documentId.value))
const documents = computed(() => legalDocuments[currentLocale.value])
const icons = {
  terms: Scale,
  privacy: ShieldCheck,
  ai: BrainCircuit,
  subscription: Scale,
  content: BookOpenText,
  security: LockKeyhole,
  minors: ShieldCheck,
  storage: LockKeyhole,
  rights: Scale,
} satisfies Record<LegalDocumentId, typeof Scale>

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/login')
}
</script>

<template>
  <main class="min-h-screen bg-slate-50 px-4 py-5 text-slate-900 sm:px-6 sm:py-8">
    <section class="mx-auto w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header class="flex items-center justify-between border-b border-slate-100 px-5 py-3.5 sm:px-7"><button type="button" class="inline-flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900" @click="goBack"><ArrowLeft class="h-4 w-4" />{{ t('returnPreviousPage') }}</button><LanguageSwitcher /></header>
      <template v-if="document">
        <article class="px-5 py-8 sm:px-10 sm:py-10"><div class="flex items-start gap-4"><span class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-950 text-white"><component :is="icons[document.id]" class="h-5 w-5" /></span><div><p class="text-xs font-semibold tracking-[0.14em] text-sky-700">{{ document.eyebrow }}</p><h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{{ document.title }}</h1><p class="mt-3 max-w-2xl text-sm leading-6 text-slate-600">{{ document.summary }}</p></div></div><div class="mt-9 space-y-8"><section v-for="section in document.sections" :key="section.title"><h2 class="text-lg font-semibold text-slate-900">{{ section.title }}</h2><p v-for="paragraph in section.paragraphs" :key="paragraph" class="mt-3 text-sm leading-7 text-slate-600">{{ paragraph }}</p><ul v-if="section.bullets" class="mt-3 space-y-2 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600"><li v-for="bullet in section.bullets" :key="bullet" class="flex gap-2"><span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-900" />{{ bullet }}</li></ul></section></div><div class="mt-10 border-t border-slate-100 pt-5 text-xs leading-5 text-slate-500">{{ currentLocale === 'zh-CN' ? '本页面为平台规则说明，不替代适用法律、院校制度或专业法律意见。' : 'This page explains platform rules and does not replace applicable law, institutional policy, or professional legal advice.' }}</div></article>
      </template>
      <template v-else>
        <div class="px-5 py-8 sm:px-10 sm:py-10"><p class="text-sm font-semibold text-sky-700">{{ t('legalCompliance') }}</p><h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{{ t('legalComplianceTitle') }}</h1><p class="mt-3 max-w-2xl text-sm leading-6 text-slate-600">{{ t('legalComplianceDescription') }}</p><div class="mt-8 grid gap-4 sm:grid-cols-2"><RouterLink v-for="item in documents" :key="item.id" :to="`/legal/${item.id}`" class="group rounded-xl border border-slate-200 p-5 transition hover:border-slate-300 hover:bg-slate-50"><component :is="icons[item.id]" class="h-5 w-5 text-slate-700" /><h2 class="mt-5 font-semibold text-slate-950">{{ item.title }}</h2><p class="mt-2 text-sm leading-6 text-slate-600">{{ item.summary }}</p><span class="mt-5 inline-flex items-center text-sm font-medium text-slate-700">{{ t('readDocument') }}<ChevronRight class="ml-1 h-4 w-4 transition group-hover:translate-x-0.5" /></span></RouterLink></div></div>
      </template>
      <footer class="flex items-center gap-2 border-t border-slate-100 px-5 py-3 text-xs text-slate-500 sm:px-7"><BookOpenText class="h-3.5 w-3.5" />{{ t('copyrightNotice') }}</footer>
    </section>
  </main>
</template>
