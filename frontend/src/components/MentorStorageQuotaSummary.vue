<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { HardDrive } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { authApi } from '@/api/client'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { MentorResourceQuota } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const quota = ref<MentorResourceQuota | null>(null)

function format(bytes: number) { return `${(bytes / 1024 / 1024).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} MB` }

onMounted(async () => {
  if (!auth.state.token) return
  try { quota.value = await authApi.mentorResourceQuota(auth.state.token) } catch { quota.value = null }
})
</script>

<template>
  <Card class="p-5 shadow-sm"><div class="flex items-center justify-between gap-3"><div class="flex items-center gap-2"><span class="grid h-9 w-9 place-items-center rounded-xl bg-violet-100 text-violet-700"><HardDrive class="h-4 w-4" /></span><div><h2 class="font-semibold text-slate-900">{{ t('resourceQuota') }}</h2><p class="text-xs text-slate-500">{{ t('storageRemaining') }}</p></div></div><RouterLink to="/mentor/resources" class="text-sm font-medium text-sky-700 hover:text-sky-800">{{ t('manageResources') }}</RouterLink></div><div v-if="quota" class="mt-4"><div class="flex justify-between text-sm"><span class="text-slate-500">{{ t('storageUsed') }}</span><span class="font-semibold text-slate-900">{{ format(quota.used_bytes) }} / {{ format(quota.quota_bytes) }}</span></div><div class="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full bg-violet-600" :style="{ width: `${Math.min(100, quota.used_bytes / quota.quota_bytes * 100)}%` }" /></div></div></Card>
</template>
