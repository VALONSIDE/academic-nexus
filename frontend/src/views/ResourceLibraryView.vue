<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Search, Sparkles } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { authApi } from '@/api/client'
import ResourceCards from '@/components/ResourceCards.vue'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'
import type { LearningResource, ResourceType } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const selectedType = ref<ResourceType | undefined>()
const search = ref('')
const recommended = ref<LearningResource[]>([])
const resources = ref<LearningResource[]>([])
const loading = ref(false)
const error = ref('')
const types: Array<ResourceType | undefined> = [undefined, 'course', 'paper', 'book']
const hasRecommended = computed(() => recommended.value.length > 0)

async function load() {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  try {
    const library = await authApi.resources(auth.state.token, selectedType.value, search.value)
    resources.value = library.items
    if (!selectedType.value && !search.value) recommended.value = (await authApi.recommendedResources(auth.state.token)).items
  } catch {
    error.value = t('updateFailed')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <DashboardLayout><div class="w-full"><div class="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><p class="text-sm font-medium text-sky-700">{{ t('learningResources') }}</p><h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900">{{ t('resourceLibrary') }}</h1><p class="mt-3 max-w-3xl leading-7 text-slate-600">{{ t('resourceLibraryDescription') }}</p></div></div>
    <Card v-if="hasRecommended" class="mt-7 border-sky-100 bg-sky-50/60 p-5 shadow-none"><div class="flex items-center gap-3"><span class="grid h-9 w-9 place-items-center rounded-xl bg-sky-600 text-white"><Sparkles class="h-4 w-4" /></span><div><h2 class="font-semibold text-slate-900">{{ t('recommendedForYou') }}</h2></div></div><ResourceCards class="mt-5" compact :resources="recommended" @error="error = $event" /></Card>
    <section class="mt-8"><div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><h2 class="text-xl font-semibold text-slate-900">{{ t('allResources') }}</h2><form class="flex w-full gap-2 sm:w-auto" @submit.prevent="load"><Input v-model="search" class="min-w-0 flex-1 sm:w-72" type="search" :placeholder="t('resourceSearchPlaceholder')" /><Button type="submit" variant="outline"><Search class="mr-1.5 h-4 w-4" />{{ t('search') }}</Button></form></div><div class="mt-4 flex flex-wrap gap-2"><Button v-for="type in types" :key="type || 'all'" size="sm" :variant="selectedType === type ? 'default' : 'outline'" type="button" @click="selectedType = type; load()">{{ type ? t(type) : t('all') }}</Button></div><div v-if="loading" class="py-12 text-center text-sm text-slate-500">{{ t('loading') }}</div><ResourceCards v-else-if="resources.length" class="mt-5" :resources="resources" @error="error = $event" /><Card v-else class="mt-5 border-dashed bg-slate-50 p-8 text-center text-sm text-slate-600 shadow-none">{{ t('resourcesEmpty') }}</Card></section><p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
  </div></DashboardLayout>
</template>
