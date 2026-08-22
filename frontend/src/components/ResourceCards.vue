<script setup lang="ts">
import { BookOpen, Download, ExternalLink, FileText, GraduationCap } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { authApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { LearningResource } from '@/types/auth'

defineProps<{ resources: LearningResource[]; compact?: boolean }>()

const emit = defineEmits<{ error: [message: string] }>()
const auth = useAuthStore()
const { t } = useI18n()

const icons = { course: GraduationCap, paper: FileText, book: BookOpen }

function formatBytes(value: number) {
  if (!value) return '0 MB'
  return `${(value / 1024 / 1024).toFixed(value < 10 * 1024 * 1024 ? 1 : 0)} MB`
}

async function download(resource: LearningResource) {
  if (!auth.state.token) return
  try {
    const file = await authApi.downloadResource(auth.state.token, resource.id)
    const url = URL.createObjectURL(file.blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = resource.file_original_name || file.filename
    anchor.click()
    URL.revokeObjectURL(url)
  } catch {
    emit('error', t('updateFailed'))
  }
}
</script>

<template>
  <div class="grid gap-4" :class="compact ? 'md:grid-cols-3' : 'lg:grid-cols-2 xl:grid-cols-3'">
    <Card v-for="resource in resources" :key="resource.id" class="flex min-w-0 flex-col p-5 shadow-sm">
      <div class="flex items-start justify-between gap-3"><span class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-sky-50 text-sky-700"><component :is="icons[resource.resource_type]" class="h-4 w-4" /></span><span v-if="resource.recommendation_score !== null" class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">{{ resource.recommendation_score }}/100</span></div>
      <p class="mt-4 text-xs font-semibold uppercase tracking-wide text-sky-700">{{ t(resource.resource_type) }}</p><h3 class="mt-1 line-clamp-2 font-semibold text-slate-900">{{ resource.title }}</h3><p class="mt-2 line-clamp-3 text-sm leading-6 text-slate-600">{{ resource.description }}</p>
      <div v-if="resource.topics.length || resource.tags.length" class="mt-4 flex flex-wrap gap-1.5"><span v-for="item in [...resource.topics, ...resource.tags].slice(0, 5)" :key="item" class="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{{ item }}</span></div>
      <p class="mt-4 text-xs text-slate-500">{{ resource.owner_name }}<span v-if="resource.file_original_name"> · {{ resource.file_original_name }} · {{ formatBytes(resource.file_size_bytes) }}</span></p>
      <div class="mt-4 flex flex-wrap gap-2"><a v-if="resource.external_url" :href="resource.external_url" target="_blank" rel="noopener noreferrer" class="inline-flex h-8 items-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50"><ExternalLink class="mr-1.5 h-3.5 w-3.5" />{{ t('openResource') }}</a><Button v-if="resource.download_url" type="button" size="sm" variant="outline" @click="download(resource)"><Download class="mr-1.5 h-3.5 w-3.5" />{{ t('downloadResource') }}</Button></div>
    </Card>
  </div>
</template>
