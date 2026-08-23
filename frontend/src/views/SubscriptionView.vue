<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CalendarClock, CheckCircle2, CreditCard, Sparkles } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'
import type { UserSubscription } from '@/types/auth'

const auth = useAuthStore()
const { t, locale } = useI18n()
const subscription = ref<UserSubscription | null>(null)
const key = ref('')
const loading = ref(false)
const redeeming = ref(false)
const error = ref('')
const notice = ref('')

const isPremium = computed(() => subscription.value?.plan_code !== 'basic')
const cycleLabel = computed(() => subscription.value
  ? `${formatDate(subscription.value.cycle_started_at)} — ${formatDate(subscription.value.cycle_ends_at)}`
  : '—')

function formatDate(value: string) {
  return new Intl.DateTimeFormat(locale.value === 'en-US' ? 'en-US' : 'zh-CN', { dateStyle: 'medium' }).format(new Date(value))
}

function subscriptionPlanLabel(plan: UserSubscription['plan_code']) {
  const keys = { basic: 'subscriptionPlanBasic', pro: 'subscriptionPlanPro', ultra: 'subscriptionPlanUltra', max: 'subscriptionPlanMax' } as const
  return t(keys[plan])
}

function errorMessage(exception: unknown) {
  if (!(exception instanceof ApiError)) return t('subscriptionRequestFailed')
  const messages: Record<string, string> = {
    subscription_key_invalid: 'subscriptionKeyInvalid',
    subscription_key_institution_mismatch: 'subscriptionKeyInstitutionMismatch',
    active_premium_plan_locked: 'premiumPlanLocked',
  }
  return t(messages[exception.code || ''] || 'subscriptionRequestFailed')
}

async function load() {
  if (!auth.state.token) return
  loading.value = true
  try {
    subscription.value = await authApi.subscription(auth.state.token)
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

async function redeem() {
  if (!auth.state.token || !key.value.trim() || redeeming.value || isPremium.value) return
  redeeming.value = true
  error.value = ''
  notice.value = ''
  try {
    subscription.value = await authApi.activateSubscriptionKey(auth.state.token, key.value)
    key.value = ''
    notice.value = t('subscriptionActivated')
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    redeeming.value = false
  }
}

onMounted(load)
</script>

<template>
  <DashboardLayout>
    <div class="mx-auto w-full max-w-5xl">
      <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p class="text-sm font-medium text-sky-700">{{ t('subscription') }}</p><h1 class="mt-1 text-3xl font-semibold tracking-tight text-slate-900">{{ t('mySubscription') }}</h1><p class="mt-3 max-w-2xl leading-7 text-slate-600">{{ t('subscriptionDescription') }}</p></div>
        <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600"><CalendarClock class="mr-2 inline h-4 w-4 text-sky-700" />{{ t('subscriptionCycle') }}: {{ cycleLabel }}</div>
      </div>

      <Card v-if="subscription" class="mt-7 overflow-hidden p-0 shadow-sm"><div class="grid gap-0 lg:grid-cols-[1.1fr_0.9fr]"><section class="bg-slate-950 p-6 text-white sm:p-8"><p class="inline-flex items-center gap-2 rounded-full bg-sky-400/15 px-3 py-1 text-xs font-semibold text-sky-200"><Sparkles class="h-3.5 w-3.5" />{{ subscriptionPlanLabel(subscription.plan_code) }}</p><h2 class="mt-5 text-3xl font-semibold">{{ subscription.credit_balance }} <span class="text-base font-medium text-slate-300">/ {{ subscription.credit_limit }} {{ t('subscriptionCredits') }}</span></h2><p class="mt-2 text-sm text-slate-300">{{ t('subscriptionCreditsUsed', { count: subscription.credits_used }) }}</p><div class="mt-6 h-2 overflow-hidden rounded-full bg-white/10"><div class="h-full rounded-full bg-sky-400" :style="{ width: `${Math.min(100, subscription.credit_balance / subscription.credit_limit * 100)}%` }" /></div></section><section class="p-6 sm:p-8"><div class="flex items-center gap-2"><CreditCard class="h-5 w-5 text-sky-700" /><h2 class="font-semibold text-slate-900">{{ t('premiumSubscription') }}</h2></div><p class="mt-3 text-sm leading-6 text-slate-600">{{ isPremium ? t('premiumPlanActiveNote') : t('premiumKeyHint') }}</p><form class="mt-5 flex flex-col gap-3 sm:flex-row" @submit.prevent="redeem"><Input v-model="key" :disabled="isPremium || redeeming" class="font-mono uppercase" maxlength="13" :placeholder="t('premiumKeyPlaceholder')" autocomplete="off" /><Button type="submit" :disabled="isPremium || redeeming || !key.trim()"><CheckCircle2 class="mr-2 h-4 w-4" />{{ redeeming ? t('loading') : t('redeemPremiumKey') }}</Button></form><p class="mt-3 text-xs leading-5 text-slate-500">{{ t('premiumPlanLockNote') }}</p></section></div></Card>
      <Card v-else-if="loading" class="mt-7 p-8 text-sm text-slate-500">{{ t('loading') }}</Card>
      <p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p><p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
    </div>
  </DashboardLayout>
</template>
