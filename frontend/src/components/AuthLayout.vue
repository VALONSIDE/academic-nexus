<script setup lang="ts">
import { GraduationCap, Sparkles } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import LanguageSwitcher from './LanguageSwitcher.vue'

const { t } = useI18n()
</script>

<template>
  <main class="relative grid min-h-screen overflow-hidden bg-slate-50 lg:grid-cols-[1.05fr_0.95fr]">
    <section class="hidden bg-slate-950 p-12 text-white lg:flex lg:flex-col">
      <div class="flex items-center gap-3 text-lg font-semibold tracking-tight">
        <span class="grid h-10 w-10 place-items-center rounded-xl bg-sky-400 text-slate-950"><GraduationCap class="h-5 w-5" /></span>
        <span>{{ t('brand') }}</span>
        <span class="text-sm font-normal text-slate-400">{{ t('brandSubtitle') }}</span>
      </div>
      <div class="my-auto max-w-xl">
        <p class="mb-5 inline-flex items-center gap-2 rounded-full border border-sky-300/20 bg-sky-300/10 px-3 py-1 text-sm text-sky-200">
          <Sparkles class="h-4 w-4" /> {{ t('heroEyebrow') }}
        </p>
        <h1 class="text-5xl font-semibold leading-tight tracking-tight">{{ t('heroTitle') }}</h1>
        <p class="mt-6 max-w-lg text-lg leading-8 text-slate-300">{{ t('heroDescription') }}</p>
      </div>
      <p class="text-sm text-slate-500">{{ t('heroFooter') }}</p>
    </section>

    <section class="flex min-h-screen flex-col px-5 py-5 sm:px-10 lg:px-16">
      <header class="flex items-center justify-between">
        <RouterLink to="/login" class="flex items-center gap-2 text-sm font-semibold text-slate-900 lg:hidden">
          <span class="grid h-8 w-8 place-items-center rounded-lg bg-slate-900 text-white"><GraduationCap class="h-4 w-4" /></span>
          {{ t('brand') }}
        </RouterLink>
        <span class="hidden lg:block" />
        <LanguageSwitcher />
      </header>
      <div class="mx-auto flex w-full max-w-md flex-1 items-center py-12">
        <slot />
      </div>
      <footer class="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span class="flex items-center gap-3"><RouterLink to="/about" class="font-medium text-slate-600 hover:text-slate-900">{{ t('about') }}</RouterLink><RouterLink to="/legal" class="font-medium text-slate-600 hover:text-slate-900">{{ t('legalCompliance') }}</RouterLink></span>
        <span>{{ t('copyrightNotice') }}</span>
      </footer>
    </section>
  </main>
</template>
