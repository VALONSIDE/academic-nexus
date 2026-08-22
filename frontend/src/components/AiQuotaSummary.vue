<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { BotMessageSquare } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { authApi } from '@/api/client'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { AiQuota } from '@/types/auth'
const auth = useAuthStore(); const { t } = useI18n(); const quota = ref<AiQuota | null>(null)
const role = computed(() => auth.state.user?.roles.includes('mentor') ? 'mentor' : 'student')
onMounted(async () => { if (auth.state.token) { try { quota.value = await authApi.aiQuota(auth.state.token) } catch { quota.value = null } } })
</script>
<template><Card class="mt-5 p-5 shadow-sm"><div class="flex items-start justify-between gap-4"><div class="flex min-w-0 items-center gap-2"><span class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-violet-100 text-violet-700"><BotMessageSquare class="h-5 w-5" /></span><div class="min-w-0"><h2 class="font-semibold text-slate-900">{{ t('aiQuota') }}</h2><p class="text-xs text-slate-500">{{ t('aiQuotaNote') }}</p></div></div><RouterLink :to="`/${role}/assistant`" class="shrink-0 whitespace-nowrap rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">{{ t('aiAssistant') }}</RouterLink></div><div v-if="quota" class="mt-4 grid grid-cols-3 divide-x divide-slate-100 text-center"><div><p class="text-xs text-slate-500">{{ t('aiDailyUsage') }}</p><p class="mt-1 font-semibold">{{ quota.daily_used }}/{{ quota.daily_limit }}</p></div><div><p class="text-xs text-slate-500">{{ t('aiDailyRemaining') }}</p><p class="mt-1 font-semibold text-sky-700">{{ quota.daily_remaining }}</p></div><div><p class="text-xs text-slate-500">{{ t('aiCreditBalance') }}</p><p class="mt-1 font-semibold">{{ quota.credit_balance }}</p></div></div></Card></template>
