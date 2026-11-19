<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { HardDriveUpload, Plus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import ResourceCards from '@/components/ResourceCards.vue'
import TagInput from '@/components/TagInput.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import Textarea from '@/components/ui/textarea/Textarea.vue'
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
const form = reactive({
  resource_type: 'course' as ResourceType,
  title: '',
  description: '',
  topics: [] as string[],
  tags: [] as string[],
  external_url: '',
  provider: '',
  level: '',
  duration_hours: '',
  duration_minutes: '',
  authors: '',
  publication: '',
  doi: '',
  publisher: '',
  isbn: '',
  publication_year: '',
})
const usagePercent = computed(() => quota.value ? Math.min(100, quota.value.used_bytes / quota.value.quota_bytes * 100) : 0)
const resourceTypeOptions = computed(() => [
  { value: 'course', label: t('course') },
  { value: 'paper', label: t('paper') },
  { value: 'book', label: t('book') },
])
const courseLevelOptions = computed(() => [
  { value: 'beginner', label: t('courseLevelBeginner') },
  { value: 'intermediate', label: t('courseLevelIntermediate') },
  { value: 'advanced', label: t('courseLevelAdvanced') },
  { value: 'all_levels', label: t('courseLevelAll') },
])

function formatBytes(value: number) {
  return `${(value / 1024 / 1024).toFixed(value < 10 * 1024 * 1024 ? 1 : 0)} MB`
}

function resetForm() {
  Object.assign(form, {
    resource_type: 'course', title: '', description: '', topics: [], tags: [], external_url: '', provider: '', level: '', duration_hours: '', duration_minutes: '',
    authors: '', publication: '', doi: '', publisher: '', isbn: '', publication_year: '',
  })
  file.value = null
}

function errorMessage(exception: unknown) {
  if (!(exception instanceof ApiError)) return t('updateFailed')
  const map: Record<string, string> = {
    resource_quota_exceeded: 'resourceQuotaExceeded', quota_below_used_storage: 'quotaBelowUsedStorage', unsupported_file_type: 'unsupportedFileType', file_too_large: 'fileTooLarge',
    invalid_resource_url: 'invalidResourceUrl', resource_location_required: 'resourceLocationRequired', invalid_course_level: 'invalidCourseLevel', invalid_course_duration: 'invalidCourseDuration',
  }
  return t(map[exception.code || ''] || 'updateFailed')
}

function validCourseDetails() {
  if (form.resource_type !== 'course') return true
  if (!form.level) {
    error.value = t('courseLevelRequired')
    return false
  }
  const hours = Number(form.duration_hours || 0)
  const minutes = Number(form.duration_minutes || 0)
  if (!Number.isInteger(hours) || !Number.isInteger(minutes) || hours < 0 || hours > 9999 || minutes < 0 || minutes >= 60 || hours + minutes === 0) {
    error.value = t('invalidCourseDuration')
    return false
  }
  return true
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
  if (!auth.state.token || !validCourseDetails()) return
  if (!file.value && !form.external_url.trim()) { error.value = t('resourceLocationRequired'); return }
  uploading.value = true
  error.value = ''
  notice.value = ''
  const payload = new FormData()
  Object.entries(form).forEach(([key, value]) => payload.append(key, Array.isArray(value) ? value.join(',') : value))
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
  <DashboardLayout>
    <div class="mx-auto w-full max-w-7xl">
      <div class="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div><p class="text-sm font-medium text-sky-700">{{ t('learningResources') }}</p><h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900">{{ t('manageResources') }}</h1><p class="mt-3 max-w-3xl leading-7 text-slate-600">{{ t('resourceQuotaDescription') }}</p></div>
        <Button type="button" @click="showForm = !showForm"><Plus class="mr-2 h-4 w-4" />{{ t('uploadResource') }}</Button>
      </div>

      <Card v-if="quota" class="mt-7 p-5">
        <div class="flex items-start justify-between gap-5"><div class="flex gap-3"><span class="grid h-10 w-10 place-items-center rounded-xl bg-sky-100 text-sky-700"><HardDriveUpload class="h-5 w-5" /></span><div><h2 class="font-semibold text-slate-900">{{ t('resourceQuota') }}</h2><p class="mt-1 text-sm text-slate-500">{{ formatBytes(quota.used_bytes) }} / {{ formatBytes(quota.quota_bytes) }}</p></div></div><div class="text-right"><p class="text-xs text-slate-500">{{ t('storageRemaining') }}</p><p class="mt-1 font-semibold text-sky-700">{{ formatBytes(quota.remaining_bytes) }}</p></div></div>
        <div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full bg-sky-600 transition-all" :style="{ width: `${usagePercent}%` }" /></div>
      </Card>

      <Card v-if="showForm" class="mt-7 p-6">
        <h2 class="font-semibold text-slate-900">{{ t('uploadResource') }}</h2>
        <p class="mt-2 text-sm text-slate-500">{{ t('resourceRequiredLegend') }}</p>
        <form class="mt-6 space-y-6" @submit.prevent="upload">
          <fieldset class="grid gap-4 rounded-xl border border-slate-200 p-4 md:grid-cols-2 sm:p-5">
            <legend class="px-2 font-semibold">{{ t('resourceCoreFields') }}</legend>
            <label class="grid gap-2 text-sm font-medium"><span>{{ t('resourceType') }} <span class="text-rose-700">*</span></span><Select v-model="form.resource_type" :options="resourceTypeOptions" /></label>
            <label class="grid gap-2 text-sm font-medium"><span>{{ t('resourceTitle') }} <span class="text-rose-700">*</span></span><Input v-model="form.title" required minlength="2" maxlength="240" /></label>
            <label class="grid gap-2 text-sm font-medium md:col-span-2"><span>{{ t('resourceDescription') }} <span class="text-slate-500">· {{ t('optional') }}</span></span><Textarea v-model="form.description" maxlength="5000" /></label>
          </fieldset>
          <fieldset class="grid gap-4 rounded-xl border border-slate-200 p-4 md:grid-cols-2 sm:p-5">
            <legend class="px-2 font-semibold">{{ t('resourceTypeFields') }}</legend>
            <template v-if="form.resource_type === 'course'">
              <label class="grid gap-2 text-sm font-medium"><span>{{ t('level') }} <span class="text-rose-700">*</span></span><Select v-model="form.level" :options="courseLevelOptions" :placeholder="t('selectCourseLevel')" /></label>
              <div class="grid gap-2 text-sm font-medium"><p>{{ t('duration') }} <span class="text-rose-700">*</span></p><div class="grid grid-cols-2 gap-3"><label class="flex items-center gap-2"><Input v-model="form.duration_hours" :aria-label="t('hours')" type="number" min="0" max="9999" /><span>{{ t('hours') }}</span></label><label class="flex items-center gap-2"><Input v-model="form.duration_minutes" :aria-label="t('minutes')" type="number" min="0" max="59" /><span>{{ t('minutes') }}</span></label></div></div>
              <label class="grid gap-2 text-sm font-medium"><span>{{ t('provider') }} · {{ t('optional') }}</span><Input v-model="form.provider" maxlength="160" /></label>
            </template>
            <template v-else>
              <label class="grid gap-2 text-sm font-medium"><span>{{ t('authors') }} · {{ t('optional') }}</span><Input v-model="form.authors" maxlength="800" /></label>
              <label v-if="form.resource_type === 'paper'" class="grid gap-2 text-sm font-medium"><span>{{ t('publication') }} · {{ t('optional') }}</span><Input v-model="form.publication" maxlength="400" /></label>
              <label v-if="form.resource_type === 'paper'" class="grid gap-2 text-sm font-medium"><span>{{ t('doi') }} · {{ t('optional') }}</span><Input v-model="form.doi" maxlength="200" /></label>
              <label v-if="form.resource_type === 'book'" class="grid gap-2 text-sm font-medium"><span>{{ t('publisher') }} · {{ t('optional') }}</span><Input v-model="form.publisher" maxlength="400" /></label>
              <label v-if="form.resource_type === 'book'" class="grid gap-2 text-sm font-medium"><span>{{ t('isbn') }} · {{ t('optional') }}</span><Input v-model="form.isbn" maxlength="64" /></label>
              <label class="grid gap-2 text-sm font-medium"><span>{{ t('publicationYear') }} · {{ t('optional') }}</span><Input v-model="form.publication_year" type="number" min="1000" max="2100" /></label>
            </template>
          </fieldset>
          <fieldset class="grid gap-4 rounded-xl border border-sky-200 bg-sky-50/40 p-4 md:grid-cols-2 sm:p-5">
            <legend class="px-2 font-semibold">{{ t('resourceDeliveryFields') }} <span class="text-rose-700">*</span></legend>
            <p class="text-sm text-slate-600 md:col-span-2">{{ t('resourceAtLeastOne') }}</p>
            <label class="grid gap-2 text-sm font-medium">{{ t('resourceUrl') }}<Input v-model="form.external_url" type="url" maxlength="2048" placeholder="https://" /></label>
            <label class="grid gap-2 text-sm font-medium">{{ t('resourceFile') }}<Input type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.zip" @change="onFile" /></label>
          </fieldset>
          <details class="rounded-xl border border-slate-200 px-4 py-3">
            <summary class="cursor-pointer font-medium">{{ t('resourceOptionalFields') }}</summary>
            <div class="mt-4 grid gap-4 md:grid-cols-2">
              <label class="grid gap-2 text-sm font-medium">{{ t('resourceTopics') }}<TagInput v-model="form.topics" :placeholder="t('tagInputPlaceholder')" /></label>
              <label class="grid gap-2 text-sm font-medium">{{ t('resourceTags') }}<TagInput v-model="form.tags" :placeholder="t('tagInputPlaceholder')" /></label>
            </div><p class="mt-2 text-xs text-slate-500">{{ t('tagInputHint') }}</p>
          </details>
          <p v-if="error" class="text-sm text-rose-700" role="alert">{{ error }}</p>
          <div class="flex justify-end gap-2"><Button type="button" variant="outline" :disabled="uploading" @click="showForm = false; resetForm()">{{ t('cancel') }}</Button><Button type="submit" :disabled="uploading">{{ uploading ? t('loading') : t('uploadResource') }}</Button></div>
        </form>
      </Card>

      <section class="mt-8"><h2 class="text-xl font-semibold text-slate-900">{{ t('manageResources') }}</h2><p v-if="loading" class="mt-5 text-sm text-slate-500">{{ t('loading') }}</p><ResourceCards v-else-if="resources.length" class="mt-5" :resources="resources" manageable @error="error = $event" @remove="remove" /><Card v-else class="mt-5 border-dashed bg-slate-50 p-8 text-center text-sm text-slate-600 shadow-none">{{ t('resourcesEmpty') }}</Card></section>
      <p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p><p v-if="error && !showForm" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
    </div>
  </DashboardLayout>
</template>
