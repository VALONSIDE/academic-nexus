<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, CheckCircle2, FileKey2, FileSpreadsheet, KeyRound, ShieldAlert, Sparkles, UserRoundCheck, UsersRound } from 'lucide-vue-next'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Select, type SelectOption } from '@/components/ui/select'
import { useAuthStore } from '@/stores/auth'
import type { InstitutionAccount, SubscriptionKeyDeliveryValidation } from '@/types/auth'

type Stage = 'import' | 'select' | 'deliver'
type DeliveryMode = 'activate' | 'pdf'

const auth = useAuthStore()
const { t } = useI18n()
const stage = ref<Stage>('import')
const mode = ref<DeliveryMode>('pdf')
const results = ref<SubscriptionKeyDeliveryValidation[]>([])
const selectedKeys = ref<string[]>([])
const recipients = ref<Record<string, string>>({})
const generalDeliveryKeys = ref<string[]>([])
const accountsByInstitution = ref<Record<string, InstitutionAccount[]>>({})
const loading = ref(false)
const submitting = ref(false)
const notice = ref('')
const error = ref('')

const available = computed(() => results.value.filter(item => item.status === 'available' && item.plan_code && item.institution_abbr))
const selectedItems = computed(() => available.value.filter(item => selectedKeys.value.includes(item.key)))
const deliveryReady = computed(() => {
  if (!selectedItems.value.length) return false
  return selectedItems.value.every(item => {
    if (mode.value === 'pdf' && generalDeliveryKeys.value.includes(item.key)) return true
    const recipient = (accountsByInstitution.value[item.institution_abbr || ''] || []).find(account => account.id === recipients.value[item.key])
    return Boolean(recipient && !recipient.has_active_premium_subscription)
  })
})

function clearSensitiveState() {
  results.value = []
  selectedKeys.value = []
  recipients.value = {}
  generalDeliveryKeys.value = []
  accountsByInstitution.value = {}
}

function errorMessage(exception: unknown) {
  if (!(exception instanceof ApiError)) return t('subscriptionDeliveryValidationFailed')
  const messages: Record<string, string> = {
    subscription_delivery_workbook_invalid: 'subscriptionDeliveryValidationFailed',
    subscription_delivery_workbook_no_keys: 'subscriptionDeliveryValidationFailed',
    subscription_delivery_recipient_ineligible: 'subscriptionDeliveryNoRecipients',
    subscription_delivery_key_unavailable: 'subscriptionKeyUnavailable',
    subscription_delivery_recipient_already_subscribed: 'subscriptionDeliveryRecipientAlreadySubscribed',
    active_premium_plan_locked: 'activePremiumPlanLocked',
    institution_scope_forbidden: 'institutionScopeForbidden',
  }
  return t(messages[exception.code || ''] || 'subscriptionDeliveryValidationFailed')
}

function statusLabel(status: SubscriptionKeyDeliveryValidation['status']) {
  return t({ available: 'subscriptionKeyAvailable', invalid: 'subscriptionKeyInvalid', unavailable: 'subscriptionKeyUnavailable', not_authorized: 'subscriptionKeyNotAuthorized' }[status])
}

function planLabel(plan: SubscriptionKeyDeliveryValidation['plan_code']) {
  if (!plan) return '—'
  return t({ pro: 'subscriptionPlanPro', ultra: 'subscriptionPlanUltra', max: 'subscriptionPlanMax' }[plan])
}

async function importReceipt(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !auth.state.token) return
  clearSensitiveState()
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    results.value = await authApi.validateSubscriptionDeliveryReceipt(auth.state.token, file)
    stage.value = 'select'
    if (!available.value.length) error.value = t('subscriptionDeliveryNoAvailable')
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

function toggleKey(key: string, checked: boolean) {
  selectedKeys.value = checked
    ? [...new Set([...selectedKeys.value, key])]
    : selectedKeys.value.filter(item => item !== key)
  if (!checked) delete recipients.value[key]
}

async function continueToRecipients() {
  if (!auth.state.token || !selectedItems.value.length) return
  loading.value = true
  error.value = ''
  try {
    const institutions = [...new Set(selectedItems.value.map(item => item.institution_abbr!))]
    const pairs = await Promise.all(institutions.map(async abbr => [abbr, await authApi.institutionAccounts(auth.state.token!, abbr)] as const))
    accountsByInstitution.value = Object.fromEntries(pairs)
    stage.value = 'deliver'
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

function recipientOptions(item: SubscriptionKeyDeliveryValidation): SelectOption[] {
  return (accountsByInstitution.value[item.institution_abbr || ''] || []).map(account => ({
    value: account.id,
    label: [
      account.full_name,
      account.username,
      t(account.role),
      account.has_active_premium_subscription ? t('subscriptionDeliveryAlreadySubscribed') : '',
    ].filter(Boolean).join(' · '),
    disabled: account.has_active_premium_subscription,
  }))
}

function setGeneralDelivery(key: string, checked: boolean) {
  generalDeliveryKeys.value = checked
    ? [...new Set([...generalDeliveryKeys.value, key])]
    : generalDeliveryKeys.value.filter(item => item !== key)
  if (checked) delete recipients.value[key]
}

function selectRecipient(key: string, value: string) {
  if (value) generalDeliveryKeys.value = generalDeliveryKeys.value.filter(item => item !== key)
}

watch(mode, value => {
  if (value === 'activate') generalDeliveryKeys.value = []
})

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

async function submitDelivery() {
  if (!auth.state.token || !deliveryReady.value) {
    error.value = t('subscriptionDeliveryNoRecipients')
    return
  }
  if (mode.value === 'activate' && !window.confirm(t('subscriptionDeliveryDirectConfirm'))) return
  submitting.value = true
  error.value = ''
  notice.value = ''
  const items = selectedItems.value.map(item => (
    mode.value === 'pdf' && generalDeliveryKeys.value.includes(item.key)
      ? { key: item.key }
      : { key: item.key, recipient_user_id: recipients.value[item.key]! }
  ))
  try {
    if (mode.value === 'activate') {
      const response = await authApi.directlyActivateSubscriptionDelivery(auth.state.token, items)
      notice.value = t('subscriptionDeliveryComplete', { count: response.activated_count })
    } else {
      const download = await authApi.exportSubscriptionDeliveryPdfs(auth.state.token, items)
      saveDownload(download.blob, download.filename)
      notice.value = t('subscriptionDeliveryPdfExported')
    }
    clearSensitiveState()
    stage.value = 'import'
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    submitting.value = false
  }
}

onBeforeUnmount(clearSensitiveState)
</script>

<template>
  <DashboardLayout>
    <div class="mx-auto w-full max-w-6xl">
      <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-200 bg-slate-950 px-6 py-7 text-white sm:px-8">
          <div class="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
            <div><div class="flex items-center gap-2 text-xs font-semibold tracking-[0.16em] text-slate-300"><FileKey2 class="h-4 w-4" />SUBSCRIPTION DELIVERY / OFFLINE</div><h1 class="mt-3 text-3xl font-semibold tracking-tight">{{ t('subscriptionDeliveryTitle') }}</h1><p class="mt-3 max-w-3xl text-sm leading-6 text-slate-300">{{ t('subscriptionDeliveryDescription') }}</p></div>
            <span class="inline-flex shrink-0 items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-xs text-slate-100"><ShieldAlert class="h-4 w-4" />{{ t('subscriptionDeliveryBrowserOnly') }}</span>
          </div>
        </div>
        <ol class="grid border-b border-slate-200 sm:grid-cols-3"><li v-for="(item, index) in [{ id: 'import', label: 'subscriptionDeliveryStepImport' }, { id: 'select', label: 'subscriptionDeliveryStepSelect' }, { id: 'deliver', label: 'subscriptionDeliveryStepDeliver' }]" :key="item.id" class="flex items-center gap-3 px-6 py-4 text-sm" :class="stage === item.id ? 'bg-slate-50 font-semibold text-slate-950' : 'text-slate-400'"><span class="grid h-6 w-6 place-items-center rounded-full border text-xs" :class="stage === item.id ? 'border-slate-950 bg-slate-950 text-white' : 'border-slate-300'">{{ index + 1 }}</span>{{ t(item.label) }}</li></ol>
      </section>

      <Card v-if="stage === 'import'" class="mt-6 p-6 sm:p-8"><div class="mx-auto max-w-2xl text-center"><span class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-slate-950 text-white"><FileSpreadsheet class="h-6 w-6" /></span><h2 class="mt-5 text-xl font-semibold text-slate-950">{{ t('uploadSubscriptionReceipt') }}</h2><p class="mt-3 text-sm leading-6 text-slate-600">{{ t('subscriptionDeliveryExcelHint') }}</p><label class="mt-6 inline-flex cursor-pointer items-center justify-center rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"><FileSpreadsheet class="mr-2 h-4 w-4" />{{ loading ? t('loading') : t('uploadSubscriptionReceipt') }}<input class="sr-only" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" :disabled="loading" @change="importReceipt" /></label></div></Card>

      <section v-else-if="stage === 'select'" class="mt-6"><Card class="overflow-hidden p-0"><div class="flex flex-col gap-3 border-b border-slate-200 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6"><div><h2 class="font-semibold text-slate-900">{{ t('subscriptionDeliveryStepSelect') }}</h2><p class="mt-1 text-sm text-slate-500">{{ t('subscriptionDeliverySelected', { count: selectedItems.length }) }}</p></div><Button type="button" :disabled="loading || !selectedItems.length" @click="continueToRecipients">{{ loading ? t('loading') : t('subscriptionDeliveryNext') }}<UsersRound class="ml-2 h-4 w-4" /></Button></div><div class="overflow-x-auto"><table class="min-w-full text-left text-sm"><thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th class="w-14 px-5 py-3 sm:px-6"></th><th class="px-3 py-3">Key</th><th class="px-3 py-3">{{ t('subscriptionTier') }}</th><th class="px-3 py-3">{{ t('institution') }}</th><th class="px-5 py-3 sm:px-6">{{ t('preRegistrationStatus') }}</th></tr></thead><tbody class="divide-y divide-slate-100"><tr v-for="item in results" :key="`${item.row_number}-${item.key}`" :class="item.status === 'available' ? 'bg-white' : 'bg-slate-50 text-slate-400'"><td class="px-5 py-4 sm:px-6"><input v-if="item.status === 'available'" :checked="selectedKeys.includes(item.key)" class="h-4 w-4 rounded border-slate-300 text-slate-950 focus:ring-slate-900" type="checkbox" :aria-label="item.key" @change="toggleKey(item.key, ($event.target as HTMLInputElement).checked)" /></td><td class="px-3 py-4 font-mono text-xs font-semibold tracking-wide text-slate-800">{{ item.key }}</td><td class="px-3 py-4">{{ planLabel(item.plan_code) }}</td><td class="px-3 py-4">{{ item.institution_name_zh || '—' }}<span v-if="item.institution_abbr" class="ml-1.5 font-mono text-xs text-slate-400">{{ item.institution_abbr }}</span></td><td class="px-5 py-4 sm:px-6"><span class="rounded-full px-2.5 py-1 text-xs font-medium" :class="item.status === 'available' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'">{{ statusLabel(item.status) }}</span></td></tr></tbody></table></div></Card></section>

      <section v-else class="mt-6">
        <div class="mb-4 flex items-center justify-between">
          <Button type="button" variant="ghost" size="sm" @click="stage = 'select'"><ArrowLeft class="mr-1.5 h-4 w-4" />{{ t('subscriptionDeliveryBack') }}</Button>
          <span class="text-sm text-slate-500">{{ t('subscriptionDeliverySelected', { count: selectedItems.length }) }}</span>
        </div>
        <div class="grid gap-6 xl:grid-cols-[1.1fr_.9fr]">
          <Card class="p-5 sm:p-6">
            <div class="flex items-center gap-2"><UserRoundCheck class="h-5 w-5 text-slate-700" /><h2 class="font-semibold text-slate-900">{{ t('subscriptionRecipient') }}</h2></div>
            <p class="mt-2 text-sm text-slate-600">{{ t('subscriptionDeliveryChooseRecipient') }}</p>
            <div class="mt-5 divide-y divide-slate-100">
              <div v-for="item in selectedItems" :key="item.key" class="grid gap-3 py-4 sm:grid-cols-[minmax(0,1fr)_minmax(15rem,.95fr)] sm:items-center">
                <div>
                  <p class="font-mono text-sm font-semibold text-slate-900">{{ item.key }}</p>
                  <p class="mt-1 text-xs text-slate-500">{{ item.institution_name_zh }} · {{ planLabel(item.plan_code) }}</p>
                  <label v-if="mode === 'pdf'" class="mt-2 inline-flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-600">
                    <input class="h-3.5 w-3.5 rounded border-slate-300 text-slate-950 focus:ring-slate-900" type="checkbox" :checked="generalDeliveryKeys.includes(item.key)" @change="setGeneralDelivery(item.key, ($event.target as HTMLInputElement).checked)" />
                    {{ t('subscriptionDeliveryGeneralPdf') }}
                  </label>
                </div>
                <Select
                  v-model="recipients[item.key]"
                  :options="recipientOptions(item)"
                  :placeholder="t('subscriptionDeliveryChooseRecipient')"
                  :disabled="generalDeliveryKeys.includes(item.key) || !recipientOptions(item).length"
                  @update:model-value="selectRecipient(item.key, $event)"
                />
              </div>
            </div>
            <p class="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-500">{{ mode === 'activate' ? t('subscriptionDeliveryActiveSubscriptionHint') : t('subscriptionDeliveryGeneralPdfHint') }}</p>
          </Card>
          <Card class="border-slate-300 p-5 sm:p-6">
            <div class="flex items-center gap-2"><Sparkles class="h-5 w-5 text-slate-700" /><h2 class="font-semibold text-slate-900">{{ t('subscriptionDeliveryMode') }}</h2></div>
            <div class="mt-5 grid gap-3">
              <button type="button" class="rounded-xl border p-4 text-left transition" :class="mode === 'pdf' ? 'border-slate-950 bg-slate-950 text-white' : 'border-slate-200 hover:border-slate-400'" @click="mode = 'pdf'"><span class="font-semibold">{{ t('subscriptionDeliveryExportPdf') }}</span><span class="mt-1 block text-sm leading-6" :class="mode === 'pdf' ? 'text-slate-300' : 'text-slate-500'">{{ t('subscriptionDeliveryExportPdfHint') }}</span></button>
              <button type="button" class="rounded-xl border p-4 text-left transition" :class="mode === 'activate' ? 'border-rose-700 bg-rose-50 text-rose-950' : 'border-slate-200 hover:border-slate-400'" @click="mode = 'activate'"><span class="font-semibold">{{ t('subscriptionDeliveryDirectActivation') }}</span><span class="mt-1 block text-sm leading-6 text-slate-500">{{ t('subscriptionDeliveryDirectActivationHint') }}</span></button>
            </div>
            <button class="mt-6 inline-flex h-10 w-full items-center justify-center rounded-lg bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800 disabled:pointer-events-none disabled:opacity-50" :class="mode === 'activate' ? 'bg-rose-700 hover:bg-rose-800' : ''" type="button" :disabled="submitting || !deliveryReady" @click="submitDelivery"><CheckCircle2 class="mr-2 h-4 w-4" />{{ submitting ? t('loading') : mode === 'activate' ? t('subscriptionDeliveryActivateAndDestroy') : t('subscriptionDeliveryExportZip') }}</button>
            <p class="mt-3 text-xs leading-5 text-slate-500">{{ t('subscriptionDeliveryBrowserOnly') }}</p>
          </Card>
        </div>
      </section>

      <p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p><p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
    </div>
  </DashboardLayout>
</template>
