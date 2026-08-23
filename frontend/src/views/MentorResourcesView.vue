<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { HardDriveUpload, Plus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { ApiError, authApi } from '@/api/client'
import ResourceCards from '@/components/ResourceCards.vue'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useAuthStore } from '@/stores/auth'
import type { LearningResource, MentorResourceQuota, ResourceType } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const quota = ref<MentorResourceQuota | null>(null)
const resources = ref<LearningResource[]>([])
const showForm = ref(false)
const uploading = ref(false)
const loading = ref(false)
const error = ref('')
const notice = ref('')
const file = ref<File | null>(null)
const form = reactive({ resource_type: 'course' as ResourceType, title: '', description: '', topics: '', tags: '', external_url: '', provider: '', level: '', duration: '', authors: '', publication: '', doi: '', publisher: '', isbn: '', publication_year: '' })
const usagePercent = computed(() => quota.value ? Math.min(100, quota.value.used_bytes / quota.value.quota_bytes * 100) : 0)
const resourceTypeOptions = computed(() => [
  { value: 'course', label: t('course') },
  { value: 'paper', label: t('paper') },
  { value: 'book', label: t('book') },
])

function formatBytes(value: number) {
  return `${(value / 1024 / 1024).toFixed(value < 10 * 1024 * 1024 ? 1 : 0)} MB`
}

function resetForm() {
  Object.assign(form, { resource_type: 'course', title: '', description: '', topics: '', tags: '', external_url: '', provider: '', level: '', duration: '', authors: '', publication: '', doi: '', publisher: '', isbn: '', publication_year: '' })
  file.value = null
}

function errorMessage(exception: unknown) {
  if (!(exception instanceof ApiError)) return t('updateFailed')
  const map: Record<string, string> = { resource_quota_exceeded: 'resourceQuotaExceeded', quota_below_used_storage: 'quotaBelowUsedStorage', unsupported_file_type: 'unsupportedFileType', file_too_large: 'fileTooLarge', invalid_resource_url: 'invalidResourceUrl', resource_location_required: 'resourceLocationRequired' }
  return t(map[exception.code || ''] || 'updateFailed')
}

async function load() {
  if (!auth.state.token) return
  loading.value = true
  try {
    const [nextQuota, nextResources] = await Promise.all([authApi.mentorResourceQuota(auth.state.token), authApi.mentorResources(auth.state.token)])
    quota.value = nextQuota
    resources.value = nextResources.items
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] || null
}

async function upload() {
  if (!auth.state.token) return
  uploading.value = true
  error.value = ''
  notice.value = ''
  const payload = new FormData()
  Object.entries(form).forEach(([key, value]) => payload.append(key, value))
  if (file.value) payload.append('file', file.value)
  try {
    const resource = await authApi.uploadMentorResource(auth.state.token, payload)
    resources.value = [resource, ...resources.value]
    quota.value = await authApi.mentorResourceQuota(auth.state.token)
    notice.value = t('uploadComplete')
    showForm.value = false
    resetForm()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    uploading.value = false
  }
}

async function remove(resource: LearningResource) {
  if (!auth.state.token) return
  error.value = ''
  try {
    await authApi.deleteMentorResource(auth.state.token, resource.id)
    resources.value = resources.value.filter(item => item.id !== resource.id)
    quota.value = await authApi.mentorResourceQuota(auth.state.token)
    notice.value = t('resourceDeleted')
  } catch (exception) {
    error.value = errorMessage(exception)
  }
}

onMounted(load)
</script>

<template>
  <DashboardLayout><div class="mx-auto w-full max-w-7xl"><div class="flex flex-col justify-between gap-5 lg:flex-row lg:items-end"><div><p class="text-sm font-medium text-sky-700">{{ t('learningResources') }}</p><h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900">{{ t('manageResources') }}</h1><p class="mt-3 max-w-3xl leading-7 text-slate-600">{{ t('resourceQuotaDescription') }}</p></div><Button type="button" @click="showForm = !showForm"><Plus class="mr-2 h-4 w-4" />{{ t('uploadResource') }}</Button></div>
    <Card v-if="quota" class="mt-7 p-5"><div class="flex items-start justify-between gap-5"><div class="flex gap-3"><span class="grid h-10 w-10 place-items-center rounded-xl bg-sky-100 text-sky-700"><HardDriveUpload class="h-5 w-5" /></span><div><h2 class="font-semibold text-slate-900">{{ t('resourceQuota') }}</h2><p class="mt-1 text-sm text-slate-500">{{ formatBytes(quota.used_bytes) }} / {{ formatBytes(quota.quota_bytes) }}</p></div></div><div class="text-right"><p class="text-xs text-slate-500">{{ t('storageRemaining') }}</p><p class="mt-1 font-semibold text-sky-700">{{ formatBytes(quota.remaining_bytes) }}</p></div></div><div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full bg-sky-600 transition-all" :style="{ width: `${usagePercent}%` }" /></div></Card>
    <Card v-if="showForm" class="mt-7 p-6"><h2 class="font-semibold text-slate-900">{{ t('uploadResource') }}</h2><form class="mt-6 grid gap-5 md:grid-cols-2" @submit.prevent="upload"><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('resourceType') }}<Select v-model="form.resource_type" :options="resourceTypeOptions" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('resourceTitle') }}<Input v-model="form.title" required /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700 md:col-span-2">{{ t('resourceDescription') }}<textarea v-model="form.description" class="min-h-24 rounded-lg border border-slate-200 px-3 py-2 text-sm" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('resourceTopics') }}<Input v-model="form.topics" :placeholder="t('tagHint')" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('resourceTags') }}<Input v-model="form.tags" :placeholder="t('tagHint')" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('resourceUrl') }}<Input v-model="form.external_url" type="url" placeholder="https://" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('resourceFile') }}<input class="h-10 rounded-lg border border-slate-200 px-3 py-2 text-sm" type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.zip" @change="onFile" /></label>
      <template v-if="form.resource_type === 'course'"><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('provider') }}<Input v-model="form.provider" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('level') }}<Input v-model="form.level" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('duration') }}<Input v-model="form.duration" /></label></template><template v-else><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('authors') }}<Input v-model="form.authors" /></label><label v-if="form.resource_type === 'paper'" class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('publication') }}<Input v-model="form.publication" /></label><label v-if="form.resource_type === 'paper'" class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('doi') }}<Input v-model="form.doi" /></label><label v-if="form.resource_type === 'book'" class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('publisher') }}<Input v-model="form.publisher" /></label><label v-if="form.resource_type === 'book'" class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('isbn') }}<Input v-model="form.isbn" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('publicationYear') }}<Input v-model="form.publication_year" type="number" min="1000" max="2100" /></label></template><p class="md:col-span-2 text-xs leading-5 text-slate-500">{{ t('resourceLocationHint') }}</p><div class="flex gap-2 md:col-span-2"><Button type="submit" :disabled="uploading">{{ uploading ? t('loading') : t('uploadResource') }}</Button><Button type="button" variant="outline" @click="showForm = false; resetForm()">{{ t('cancel') }}</Button></div></form></Card>
    <section class="mt-8"><h2 class="text-xl font-semibold text-slate-900">{{ t('manageResources') }}</h2><p v-if="loading" class="mt-5 text-sm text-slate-500">{{ t('loading') }}</p><ResourceCards v-else-if="resources.length" class="mt-5" :resources="resources" manageable @error="error = $event" @remove="remove" /><Card v-else class="mt-5 border-dashed bg-slate-50 p-8 text-center text-sm text-slate-600 shadow-none">{{ t('resourcesEmpty') }}</Card></section><p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p><p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
  </div></DashboardLayout>
</template>
