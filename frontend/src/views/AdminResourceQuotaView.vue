<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { HardDrive, Search } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'
import type { AdminResourceQuotaUser } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const users = ref<AdminResourceQuotaUser[]>([])
const search = ref('')
const loading = ref(false)
const saving = ref<string | null>(null)
const error = ref('')
const notice = ref('')
const quotas = reactive<Record<string, string>>({})

function megabytes(bytes: number) { return Math.ceil(bytes / 1024 / 1024) }
function formatBytes(bytes: number) { return `${(bytes / 1024 / 1024).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} MB` }

async function load() {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  try {
    users.value = (await authApi.adminResourceQuotas(auth.state.token, search.value)).items
    users.value.forEach(user => { quotas[user.user_id] = String(megabytes(user.quota_bytes)) })
  } catch {
    error.value = t('updateFailed')
  } finally { loading.value = false }
}

async function save(user: AdminResourceQuotaUser) {
  if (!auth.state.token) return
  saving.value = user.user_id
  error.value = ''
  notice.value = ''
  try {
    const quota = await authApi.updateAdminResourceQuota(auth.state.token, user.user_id, Number(quotas[user.user_id]))
    Object.assign(user, quota)
    notice.value = t('quotaSaved')
  } catch (exception) {
    error.value = exception instanceof ApiError && exception.code === 'quota_below_used_storage' ? t('quotaBelowUsedStorage') : t('updateFailed')
  } finally { saving.value = null }
}

onMounted(load)
</script>

<template>
  <DashboardLayout><div class="w-full"><div class="flex items-start gap-3"><span class="grid h-10 w-10 place-items-center rounded-xl bg-sky-100 text-sky-700"><HardDrive class="h-5 w-5" /></span><div><h1 class="text-3xl font-semibold tracking-tight text-slate-900">{{ t('resourceQuotaManagement') }}</h1><p class="mt-3 max-w-4xl leading-7 text-slate-600">{{ t('resourceQuotaManagementDescription') }}</p></div></div><Card class="mt-7 overflow-hidden"><form class="flex gap-2 border-b border-slate-200 p-4" @submit.prevent="load"><Input v-model="search" class="min-w-0 flex-1" type="search" :placeholder="t('searchUsersPlaceholder')" /><Button type="submit" variant="outline" :disabled="loading"><Search class="mr-1.5 h-4 w-4" />{{ t('search') }}</Button></form><div v-if="loading" class="p-6 text-sm text-slate-500">{{ t('loading') }}</div><div v-else-if="!users.length" class="p-8 text-center text-sm text-slate-500">{{ t('noUsers') }}</div><div v-else class="divide-y divide-slate-100"><div v-for="user in users" :key="user.user_id" class="grid gap-4 p-5 md:grid-cols-[minmax(0,1fr)_auto_auto]"><div><p class="font-medium text-slate-900">{{ user.full_name }}</p><p class="mt-1 text-sm text-slate-500">{{ user.username }}</p><p class="mt-2 text-xs text-slate-500">{{ t('storageUsed') }}: {{ formatBytes(user.used_bytes) }} / {{ formatBytes(user.quota_bytes) }}</p></div><label class="grid content-start gap-1 text-sm font-medium text-slate-700">MB<Input v-model="quotas[user.user_id]" class="w-28" type="number" min="1" max="2048" /></label><Button class="self-start" type="button" :disabled="saving === user.user_id" @click="save(user)">{{ saving === user.user_id ? t('loading') : t('save') }}</Button></div></div></Card><p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p><p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p></div></DashboardLayout>
</template>
