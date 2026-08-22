<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Download, FileSpreadsheet, Search, Trash2, Upload } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import ErrorDialog from '@/components/ErrorDialog.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { PreRegistrationAccount } from '@/types/auth'

const auth = useAuthStore()
const { t, locale } = useI18n()
const selectedFile = ref<File | null>(null)
const statusMessage = ref('')
const error = ref('')
const errorDetails = ref<string[]>([])
const busy = ref(false)
const loadingAccounts = ref(false)
const accounts = ref<PreRegistrationAccount[]>([])
const selectedIds = ref<string[]>([])
const roleFilter = ref<'student' | 'mentor' | ''>('')
const statusFilter = ref<'issued' | 'activated' | 'revoked' | ''>('')
const accountSearch = ref('')
const fileName = computed(() => selectedFile.value?.name || t('chooseFile'))

function saveDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function pickFile(event: Event) {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] || null
  statusMessage.value = ''
  error.value = ''
  errorDetails.value = []
}

async function downloadTemplate() {
  if (!auth.state.token) return
  busy.value = true
  error.value = ''
  errorDetails.value = []
  try {
    const download = await authApi.downloadTemplate(auth.state.token)
    saveDownload(download.blob, download.filename)
  } catch {
    error.value = t('templateDownloadFailed')
  } finally {
    busy.value = false
  }
}

async function importWorkbook() {
  if (!auth.state.token || !selectedFile.value) return
  busy.value = true
  error.value = ''
  errorDetails.value = []
  statusMessage.value = ''
  try {
    const download = await authApi.importPreRegistrations(auth.state.token, selectedFile.value)
    saveDownload(download.blob, download.filename)
    statusMessage.value = t('importCompleted', { count: download.count || 0 })
    await loadAccounts()
  } catch (exception) {
    error.value = t('importFailed')
    if (exception instanceof ApiError && exception.details.length) {
      errorDetails.value = exception.details.map((detail) => {
        const parts = detail.split(' / ')
        return locale.value === 'zh-CN' ? (parts[0] || t('importFailed')) : (parts[1] || parts[0] || t('importFailed'))
      })
    } else {
      errorDetails.value = [error.value]
    }
  } finally {
    busy.value = false
  }
}

async function loadAccounts() {
  if (!auth.state.token) return
  loadingAccounts.value = true
  try {
    const result = await authApi.preRegistrations(auth.state.token, { role: roleFilter.value || undefined, account_status: statusFilter.value || undefined, search: accountSearch.value.trim() || undefined })
    accounts.value = result.items
    selectedIds.value = selectedIds.value.filter((id) => result.items.some((item) => item.id === id && item.status === 'issued'))
  } catch { error.value = t('updateFailed') } finally { loadingAccounts.value = false }
}

async function deleteAccounts(ids: string[]) {
  if (!auth.state.token || !ids.length) return
  const firstId = ids[0]
  if (!firstId) return
  const prompt = locale.value === 'zh-CN' ? `确认删除 ${ids.length} 个未激活预注册账户？此操作不可恢复。` : `Delete ${ids.length} unactivated pre-registration account(s)? This cannot be undone.`
  if (!window.confirm(prompt)) return
  busy.value = true; error.value = ''
  try {
    if (ids.length === 1) await authApi.deletePreRegistration(auth.state.token, firstId)
    else await authApi.deletePreRegistrations(auth.state.token, ids)
    selectedIds.value = []
    await loadAccounts()
  } catch (exception) {
    error.value = exception instanceof ApiError && exception.code === 'activated_pre_registration_cannot_be_deleted' ? t('deletePreRegistrationHint') : t('updateFailed')
  } finally { busy.value = false }
}

onMounted(loadAccounts)
</script>

<template>
  <DashboardLayout>
    <div class="max-w-5xl">
      <h1 class="text-3xl font-semibold tracking-tight text-slate-900">{{ t('templateTitle') }}</h1>
      <p class="mt-3 leading-7 text-slate-600">{{ t('templateDescription') }}</p>
      <p class="mt-2 text-sm font-medium text-sky-700">{{ t('roleSeparationDescription') }}</p>

      <Card class="mt-8 p-6">
        <div class="flex items-start gap-4">
          <span class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-sky-100 text-sky-800"><FileSpreadsheet class="h-5 w-5" /></span>
          <div>
            <h2 class="font-semibold text-slate-900">{{ t('templateStep') }}</h2>
            <p class="mt-1 text-sm leading-6 text-slate-600">{{ t('templateStepDescription') }}</p>
            <Button class="mt-4" variant="outline" type="button" :disabled="busy" @click="downloadTemplate"><Download class="mr-2 h-4 w-4" />{{ t('downloadTemplate') }}</Button>
          </div>
        </div>
      </Card>

      <Card class="mt-5 p-6">
        <div class="flex items-start gap-4">
          <span class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-700"><Upload class="h-5 w-5" /></span>
          <div class="w-full">
            <h2 class="font-semibold text-slate-900">{{ t('importStep') }}</h2>
            <p class="mt-1 text-sm leading-6 text-slate-600">{{ t('importStepDescription') }}</p>
            <input id="pre-registration-file" class="sr-only" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" @change="pickFile" />
            <label for="pre-registration-file" class="mt-4 flex cursor-pointer items-center justify-between rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-3 text-sm text-slate-700 hover:bg-slate-100">
              <span class="truncate">{{ fileName }}</span><span class="ml-4 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white">{{ t('chooseFile') }}</span>
            </label>
            <Button class="mt-4" type="button" :disabled="busy || !selectedFile" @click="importWorkbook"><Upload class="mr-2 h-4 w-4" />{{ busy ? t('loading') : t('importAndDownload') }}</Button>
          </div>
        </div>
        <p v-if="statusMessage" class="mt-5 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{{ statusMessage }}</p>
        <p v-if="error && !errorDetails.length" class="mt-5 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{{ error }}</p>
      </Card>
      <Card class="mt-7 overflow-hidden"><div class="flex flex-col justify-between gap-4 border-b border-slate-200 p-5 lg:flex-row lg:items-center"><div><h2 class="font-semibold text-slate-900">{{ t('preRegistrationAccounts') }}</h2><p class="mt-1 text-sm text-slate-500">{{ t('deletePreRegistrationHint') }}</p></div><Button v-if="selectedIds.length" variant="outline" :disabled="busy" @click="deleteAccounts(selectedIds)"><Trash2 class="mr-2 h-4 w-4" />{{ t('deleteSelected') }} ({{ selectedIds.length }})</Button></div><form class="grid gap-3 border-b border-slate-100 p-4 md:grid-cols-[minmax(0,1fr)_10rem_10rem_auto]" @submit.prevent="loadAccounts"><label class="relative"><Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input v-model="accountSearch" class="h-10 w-full rounded-lg border border-slate-200 pl-9 pr-3 text-sm outline-none focus:border-sky-500" :placeholder="t('searchUsersPlaceholder')" /></label><select v-model="roleFilter" class="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm"><option value="">{{ t('all') }}</option><option value="student">{{ t('student') }}</option><option value="mentor">{{ t('mentor') }}</option></select><select v-model="statusFilter" class="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm"><option value="">{{ t('preRegistrationStatus') }}</option><option value="issued">{{ t('issued') }}</option><option value="activated">{{ t('activated') }}</option></select><Button type="submit" variant="outline" :disabled="loadingAccounts">{{ t('search') }}</Button></form><div v-if="loadingAccounts" class="p-8 text-center text-sm text-slate-500">{{ t('loading') }}</div><div v-else-if="!accounts.length" class="p-8 text-center text-sm text-slate-500">{{ t('noUsers') }}</div><div v-else class="divide-y divide-slate-100"><div v-for="item in accounts" :key="item.id" class="grid gap-3 p-5 md:grid-cols-[auto_minmax(0,1fr)_auto]"><input v-if="item.status === 'issued'" v-model="selectedIds" :value="item.id" type="checkbox" class="mt-1 h-4 w-4" /><span v-else class="mt-1 h-4 w-4" /><div class="min-w-0"><p class="font-medium text-slate-900">{{ item.full_name }} <span class="ml-2 rounded-full px-2 py-1 text-xs" :class="item.status === 'activated' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'">{{ t(item.status) }}</span></p><p class="mt-1 truncate text-sm text-slate-500">{{ item.username }} · {{ item.academic_id }} · {{ t(item.role_code) }}</p><p class="mt-1 text-xs text-slate-500">{{ item.institution_name_zh }} · {{ item.college_name_zh }} ({{ item.institution_abbr }})</p></div><Button v-if="item.status === 'issued'" size="sm" variant="ghost" :disabled="busy" @click="deleteAccounts([item.id])"><Trash2 class="mr-1.5 h-4 w-4" />{{ t('deleteResource') }}</Button></div></div></Card>
    </div>
    <ErrorDialog v-if="errorDetails.length" :title="t('importValidationTitle')" :details="errorDetails" :close-label="t('close')" @close="errorDetails = []" />
  </DashboardLayout>
</template>
