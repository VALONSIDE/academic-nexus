<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { SlidersHorizontal } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'
import type { AdminAiQuotaListResponse, AdminAiQuotaUser } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const role = ref<'student' | 'mentor' | undefined>(undefined)
const roleOptions: Array<'student' | 'mentor' | undefined> = [undefined, 'student', 'mentor']
const search = ref('')
const data = ref<AdminAiQuotaListResponse | null>(null)
const selected = ref<AdminAiQuotaUser | null>(null)
const form = reactive({ plan_code: 'basic', daily_limit: '20', daily_used: '0', credit_balance: '100' })
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const projectLabel = computed(() => data.value ? `${data.value.project_daily_used}/${data.value.project_daily_limit}` : '—')

function selectUser(user: AdminAiQuotaUser) {
  selected.value = user
  form.plan_code = user.plan_code
  form.daily_limit = String(user.daily_limit)
  form.daily_used = String(user.daily_used)
  form.credit_balance = String(user.credit_balance)
  error.value = ''
  notice.value = ''
}

async function load() {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  try {
    data.value = await authApi.adminAiQuotas(auth.state.token, role.value, search.value)
    if (selected.value) {
      const refreshed = data.value.items.find(item => item.user_id === selected.value?.user_id)
      if (refreshed) selectUser(refreshed)
      else selected.value = null
    }
  } catch (exception) {
    error.value = exception instanceof ApiError && exception.code === 'project_daily_limit_reached' ? t('aiProjectLimitReached') : t('updateFailed')
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!auth.state.token || !selected.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await authApi.updateAdminAiQuota(auth.state.token, selected.value.user_id, {
      plan_code: form.plan_code,
      daily_limit: Number(form.daily_limit),
      daily_used: Number(form.daily_used),
      credit_balance: Number(form.credit_balance),
    })
    selected.value = { ...selected.value, plan_code: result.plan_code, daily_limit: result.daily_limit, daily_used: result.daily_used, credit_balance: result.credit_balance }
    if (data.value) data.value.items = data.value.items.map(item => item.user_id === selected.value?.user_id ? selected.value as AdminAiQuotaUser : item)
    notice.value = t('quotaSaved')
    await load()
  } catch (exception) {
    error.value = exception instanceof ApiError && exception.code === 'project_daily_limit_reached' ? t('aiProjectLimitReached') : t('updateFailed')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <DashboardLayout>
    <div>
      <div class="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div><h1 class="text-3xl font-semibold tracking-tight text-slate-900">{{ t('aiQuotaManagement') }}</h1><p class="mt-3 max-w-4xl leading-7 text-slate-600">{{ t('aiQuotaManagementDescription') }}</p></div>
        <Card class="px-5 py-3 shadow-none"><p class="text-xs text-slate-500">{{ t('aiProjectCapacity') }}</p><p class="mt-1 text-xl font-semibold text-sky-700">{{ projectLabel }}</p></Card>
      </div>
      <Card class="mt-7 overflow-hidden">
        <form class="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row" @submit.prevent="load">
          <Input v-model="search" class="min-w-0 flex-1" type="search" :placeholder="t('searchUsersPlaceholder')" />
          <div class="flex shrink-0 rounded-xl bg-slate-100 p-1"><button v-for="option in roleOptions" :key="option || 'all'" type="button" class="whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium" :class="role === option ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'" @click="role = option; load()">{{ option ? t(option) : t('all') }}</button></div>
          <Button class="whitespace-nowrap" type="submit" variant="outline" :disabled="loading">{{ t('search') }}</Button>
        </form>
        <div v-if="loading" class="p-6 text-sm text-slate-500">{{ t('loading') }}</div>
        <div v-else-if="!data?.items.length" class="p-8 text-center text-sm text-slate-500">{{ t('noUsers') }}</div>
        <div v-else class="divide-y divide-slate-100">
          <button v-for="user in data.items" :key="user.user_id" type="button" class="grid w-full grid-cols-[minmax(0,1fr)_auto] gap-4 px-5 py-4 text-left hover:bg-slate-50" :class="selected?.user_id === user.user_id ? 'bg-sky-50' : ''" @click="selectUser(user)"><span><span class="block font-medium text-slate-900">{{ user.full_name }}</span><span class="mt-1 block text-sm text-slate-500">{{ user.username }} · {{ t(user.role) }}</span></span><span class="text-right text-sm"><span class="block font-semibold text-slate-900">{{ user.daily_used }}/{{ user.daily_limit }}</span><span class="text-slate-500">{{ user.credit_balance }}</span></span></button>
        </div>
      </Card>
      <Card v-if="selected" class="mt-7 max-w-3xl p-6">
        <div class="flex items-center gap-2"><SlidersHorizontal class="h-5 w-5 text-sky-700" /><h2 class="font-semibold text-slate-900">{{ selected.full_name }}</h2></div>
        <form class="mt-6 grid gap-5 sm:grid-cols-2" @submit.prevent="save">
          <label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('planCode') }}<Input v-model="form.plan_code" required /></label>
          <label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('dailyLimit') }}<Input v-model="form.daily_limit" type="number" min="1" max="500" required /></label>
          <label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('dailyUsed') }}<Input v-model="form.daily_used" type="number" min="0" max="500" required /></label>
          <label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('creditBalance') }}<Input v-model="form.credit_balance" type="number" min="0" max="100000" required /></label>
          <div class="sm:col-span-2"><Button type="submit" :disabled="saving">{{ saving ? t('loading') : t('saveQuota') }}</Button></div>
        </form>
      </Card>
      <p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p>
      <p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
    </div>
  </DashboardLayout>
</template>
