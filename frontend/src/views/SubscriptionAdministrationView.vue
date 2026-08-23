<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { CreditCard, Download, KeyRound, Landmark, RotateCcw, ShieldCheck } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, type SelectOption } from '@/components/ui/select'
import { useAuthStore } from '@/stores/auth'
import type { InstitutionOption, InstitutionSubscriptionAllocation, PremiumSubscriptionKey, PremiumSubscriptionPlan } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const allocations = ref<InstitutionSubscriptionAllocation[]>([])
const institutions = ref<InstitutionOption[]>([])
const keys = ref<PremiumSubscriptionKey[]>([])
const selectedInstitution = ref('')
const selectedPlan = ref<PremiumSubscriptionPlan>('pro')
const selectedQuantity = ref('1')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const allocationForm = reactive({ pro_credits: '0', ultra_credits: '0', max_credits: '0' })

const isSuperAdmin = computed(() => {
  const roles = auth.state.user?.roles || []
  return roles.includes('admin') || roles.includes('super_admin')
})
const institutionOptions = computed<SelectOption[]>(() => institutions.value.map(item => ({ value: item.institution_abbr, label: `${item.institution_name_zh} · ${item.institution_abbr}` })))
const planOptions = computed<SelectOption[]>(() => [
  { value: 'pro', label: 'Pro · 50' },
  { value: 'ultra', label: 'Ultra · 100' },
  { value: 'max', label: 'Max · 200' },
])
const currentInstitution = computed(() => institutions.value.find(item => item.institution_abbr === selectedInstitution.value))
const currentAllocation = computed(() => allocations.value.find(item => item.institution_abbr === selectedInstitution.value))
const availableInventory = computed(() => currentAllocation.value?.[`${selectedPlan.value}_credits` as const] || 0)
const requestedQuantity = computed(() => Number(selectedQuantity.value))
const quantityIsValid = computed(() => Number.isInteger(requestedQuantity.value) && requestedQuantity.value >= 1 && requestedQuantity.value <= Math.min(availableInventory.value, 1000))
const filteredKeys = computed(() => keys.value.filter(item => item.institution_abbr === selectedInstitution.value))

function statusLabel(status: PremiumSubscriptionKey['status']) {
  if (status === 'issued') return t('issued')
  return status === 'activated' ? t('subscriptionKeyActivated') : t('subscriptionKeyRevoked')
}

function subscriptionPlanLabel(plan: PremiumSubscriptionPlan) {
  const labels = { pro: 'subscriptionPlanPro', ultra: 'subscriptionPlanUltra', max: 'subscriptionPlanMax' } as const
  return t(labels[plan])
}

function errorMessage(exception: unknown) {
  if (!(exception instanceof ApiError)) return t('subscriptionRequestFailed')
  const messages: Record<string, string> = {
    subscription_inventory_exhausted: 'subscriptionInventoryExhausted',
    institution_scope_forbidden: 'institutionScopeForbidden',
    subscription_key_not_reclaimable: 'subscriptionKeyNotReclaimable',
  }
  return t(messages[exception.code || ''] || 'subscriptionRequestFailed')
}

function synchronizeSelection() {
  const allocation = currentAllocation.value
  allocationForm.pro_credits = String(allocation?.pro_credits || 0)
  allocationForm.ultra_credits = String(allocation?.ultra_credits || 0)
  allocationForm.max_credits = String(allocation?.max_credits || 0)
}

async function load() {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  try {
    const [nextAllocations, nextKeys, nextInstitutions] = await Promise.all([
      authApi.subscriptionAllocations(auth.state.token),
      authApi.premiumSubscriptionKeys(auth.state.token),
      isSuperAdmin.value
        ? authApi.subscriptionInstitutions(auth.state.token)
        : authApi.myInstitutionAdminScopes(auth.state.token).then(scopes => scopes.map(item => ({ institution_abbr: item.institution_abbr, institution_name_zh: item.institution_name_zh }))),
    ])
    allocations.value = nextAllocations
    keys.value = nextKeys
    institutions.value = nextInstitutions.filter((item, index, list) => list.findIndex(candidate => candidate.institution_abbr === item.institution_abbr) === index)
    if (!institutions.value.some(item => item.institution_abbr === selectedInstitution.value)) selectedInstitution.value = institutions.value[0]?.institution_abbr || ''
    synchronizeSelection()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

async function saveAllocation() {
  if (!auth.state.token || !isSuperAdmin.value || !selectedInstitution.value || !currentInstitution.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await authApi.saveSubscriptionAllocation(auth.state.token, selectedInstitution.value, {
      pro_credits: Number(allocationForm.pro_credits),
      ultra_credits: Number(allocationForm.ultra_credits),
      max_credits: Number(allocationForm.max_credits),
    })
    notice.value = t('subscriptionAllocationSaved')
    await load()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    saving.value = false
  }
}

function saveDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

async function issueKeys() {
  const quantity = requestedQuantity.value
  if (!auth.state.token || !selectedInstitution.value || !quantityIsValid.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const receipt = await authApi.issuePremiumSubscriptionKeysReceipt(auth.state.token, { institution_abbr: selectedInstitution.value, plan_code: selectedPlan.value, quantity })
    saveDownload(receipt.blob, receipt.filename)
    notice.value = t('subscriptionKeyIssued')
    await load()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    saving.value = false
  }
}

async function revokeKey(item: PremiumSubscriptionKey) {
  if (!auth.state.token || item.status !== 'issued' || saving.value || !window.confirm(t('revokeSubscriptionKeyConfirm'))) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await authApi.revokePremiumSubscriptionKey(auth.state.token, item.id)
    notice.value = t('subscriptionKeyReclaimed')
    await load()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    saving.value = false
  }
}

watch(selectedInstitution, synchronizeSelection)
onMounted(load)
</script>

<template>
  <DashboardLayout>
    <div class="mx-auto w-full max-w-7xl">
      <div class="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><p class="text-sm font-medium text-sky-700">{{ t('subscription') }}</p><h1 class="mt-1 text-3xl font-semibold tracking-tight text-slate-900">{{ t('subscriptionManagement') }}</h1><p class="mt-3 max-w-3xl leading-7 text-slate-600">{{ isSuperAdmin ? t('superSubscriptionManagementDescription') : t('institutionSubscriptionManagementDescription') }}</p></div><span class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700"><ShieldCheck class="h-4 w-4 text-sky-700" />{{ isSuperAdmin ? t('superAdministrator') : t('institutionAdministrator') }}</span></div>

      <div v-if="loading" class="mt-7 rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500">{{ t('loading') }}</div>
      <template v-else>
        <Card class="mt-7 p-5 sm:p-6"><div class="flex items-start gap-3"><span class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-sky-50 text-sky-700"><Landmark class="h-5 w-5" /></span><div><h2 class="font-semibold text-slate-900">{{ t('institution') }}</h2><p class="mt-1 text-sm leading-6 text-slate-600">{{ isSuperAdmin ? t('subscriptionAllocationHint') : t('institutionSubscriptionManagementDescription') }}</p></div></div><div class="mt-5 max-w-xl"><Select v-model="selectedInstitution" :options="institutionOptions" :placeholder="t('selectInstitution')" :disabled="!institutionOptions.length" /></div><p v-if="!institutionOptions.length" class="mt-3 text-sm text-slate-500">{{ t('selectInstitutionFirst') }}</p></Card>

        <section v-if="selectedInstitution" class="mt-6 grid gap-6 xl:grid-cols-[.9fr_1.1fr]">
          <Card v-if="isSuperAdmin" class="p-5 sm:p-6"><div class="flex items-center gap-2"><CreditCard class="h-5 w-5 text-sky-700" /><h2 class="font-semibold text-slate-900">{{ t('institutionSubscriptionAllocation') }}</h2></div><p class="mt-2 text-sm text-slate-600">{{ currentInstitution?.institution_name_zh }} · {{ selectedInstitution }}</p><form class="mt-5 grid gap-4 sm:grid-cols-3" @submit.prevent="saveAllocation"><label class="grid gap-1.5 text-sm font-medium text-slate-700">Pro<Input v-model="allocationForm.pro_credits" min="0" max="100000" type="number" required /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">Ultra<Input v-model="allocationForm.ultra_credits" min="0" max="100000" type="number" required /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">Max<Input v-model="allocationForm.max_credits" min="0" max="100000" type="number" required /></label><div class="sm:col-span-3"><Button type="submit" :disabled="saving">{{ saving ? t('loading') : t('saveSubscriptionAllocation') }}</Button></div></form></Card>

          <Card class="p-5 sm:p-6" :class="!isSuperAdmin ? 'xl:col-span-2' : ''"><div class="flex items-center gap-2"><KeyRound class="h-5 w-5 text-sky-700" /><h2 class="font-semibold text-slate-900">{{ t('issuePremiumSubscriptionKey') }}</h2></div><p class="mt-2 text-sm leading-6 text-slate-600">{{ t('issuePremiumSubscriptionKeyHint') }}</p><form class="mt-5 grid gap-4 sm:grid-cols-3" @submit.prevent="issueKeys"><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('subscriptionTier') }}<Select v-model="selectedPlan" :options="planOptions" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('subscriptionQuantity') }}<Input v-model="selectedQuantity" min="1" :max="Math.min(availableInventory, 1000)" step="1" type="number" inputmode="numeric" :disabled="!availableInventory" required /></label><div class="flex items-end"><Button class="w-full" type="submit" :disabled="saving || !quantityIsValid"><Download class="mr-2 h-4 w-4" />{{ saving ? t('loading') : t('issueAndExportSubscriptionKeys') }}</Button></div></form><p class="mt-3 text-sm text-slate-500">{{ t('availableSubscriptionInventory', { count: availableInventory }) }}</p></Card>
        </section>

        <Card v-if="selectedInstitution" class="mt-6 overflow-hidden p-0"><div class="flex items-center justify-between border-b border-slate-200 px-5 py-5 sm:px-6"><div><h2 class="font-semibold text-slate-900">{{ t('premiumSubscriptionKeys') }}</h2><p class="mt-1 text-sm text-slate-500">{{ t('subscriptionKeyHistoryHint') }}</p></div><span class="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-600">{{ filteredKeys.length }}</span></div><div v-if="filteredKeys.length" class="divide-y divide-slate-100"><div v-for="item in filteredKeys" :key="item.id" class="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between"><div><div class="flex items-center gap-2"><span class="font-medium text-slate-900">{{ subscriptionPlanLabel(item.plan_code) }}</span><span class="rounded-full px-2 py-0.5 text-xs" :class="item.status === 'activated' ? 'bg-emerald-100 text-emerald-800' : item.status === 'revoked' ? 'bg-slate-200 text-slate-600' : 'bg-amber-100 text-amber-800'">{{ statusLabel(item.status) }}</span></div><p class="mt-1 text-sm text-slate-500">{{ item.issued_at }}</p></div><Button v-if="item.status === 'issued'" type="button" size="sm" variant="outline" :disabled="saving" @click="revokeKey(item)"><RotateCcw class="mr-1.5 h-3.5 w-3.5" />{{ t('reclaimSubscriptionKey') }}</Button></div></div><div v-else class="p-10 text-center text-sm text-slate-500">{{ t('subscriptionKeysEmpty') }}</div></Card>
      </template>
      <p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p><p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
    </div>
  </DashboardLayout>
</template>
