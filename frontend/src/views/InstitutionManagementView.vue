<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Landmark, ShieldCheck, Trash2, UserRoundPlus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Select, type SelectOption } from '@/components/ui/select'
import { useAuthStore } from '@/stores/auth'
import type { InstitutionAccount, InstitutionAdminScope, InstitutionOption } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const institutions = ref<InstitutionOption[]>([])
const scopes = ref<InstitutionAdminScope[]>([])
const accounts = ref<InstitutionAccount[]>([])
const selectedInstitution = ref('')
const selectedAccount = ref('')
const loading = ref(false)
const saving = ref(false)
const notice = ref('')
const error = ref('')

const institutionOptions = computed<SelectOption[]>(() => institutions.value.map(item => ({
  value: item.institution_abbr,
  label: `${item.institution_name_zh} · ${item.institution_abbr}`,
})))
const accountOptions = computed<SelectOption[]>(() => accounts.value.map(item => ({
  value: item.id,
  label: `${item.full_name} · ${item.username} · ${t(item.role)}`,
})))
const selectedInstitutionName = computed(() => institutions.value.find(item => item.institution_abbr === selectedInstitution.value)?.institution_name_zh || '')
const selectedScopes = computed(() => scopes.value.filter(item => item.institution_abbr === selectedInstitution.value))

function errorMessage(exception: unknown) {
  if (!(exception instanceof ApiError)) return t('subscriptionRequestFailed')
  const messages: Record<string, string> = {
    institution_not_found: 'subscriptionRequestFailed',
    institution_admin_user_ineligible: 'institutionAdminUserIneligible',
  }
  return t(messages[exception.code || ''] || 'subscriptionRequestFailed')
}

async function loadAccounts() {
  accounts.value = []
  selectedAccount.value = ''
  if (!auth.state.token || !selectedInstitution.value) return
  try {
    accounts.value = await authApi.institutionAccounts(auth.state.token, selectedInstitution.value)
  } catch (exception) {
    error.value = errorMessage(exception)
  }
}

async function load() {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  try {
    const [nextInstitutions, nextScopes] = await Promise.all([
      authApi.subscriptionInstitutions(auth.state.token),
      authApi.institutionAdminScopes(auth.state.token),
    ])
    institutions.value = nextInstitutions
    scopes.value = nextScopes
    if (!nextInstitutions.some(item => item.institution_abbr === selectedInstitution.value)) {
      selectedInstitution.value = nextInstitutions[0]?.institution_abbr || ''
    }
    await loadAccounts()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

async function assignAdministrator() {
  if (!auth.state.token || !selectedInstitution.value || !selectedAccount.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await authApi.assignInstitutionAdmin(auth.state.token, {
      institution_abbr: selectedInstitution.value,
      user_id: selectedAccount.value,
    })
    notice.value = t('institutionAdminAssigned')
    await load()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    saving.value = false
  }
}

async function removeAdministrator(scope: InstitutionAdminScope) {
  if (!auth.state.token || saving.value || !window.confirm(t('removeInstitutionAdministratorConfirm'))) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await authApi.removeInstitutionAdmin(auth.state.token, scope.id)
    notice.value = t('institutionAdminRemoved')
    await load()
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    saving.value = false
  }
}

watch(selectedInstitution, () => { void loadAccounts() })
onMounted(load)
</script>

<template>
  <DashboardLayout>
    <div class="mx-auto w-full max-w-6xl">
      <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p class="text-sm font-medium text-sky-700">{{ t('institutionManagement') }}</p><h1 class="mt-1 text-3xl font-semibold tracking-tight text-slate-900">{{ t('institutionManagement') }}</h1><p class="mt-3 max-w-3xl leading-7 text-slate-600">{{ t('institutionManagementDescription') }}</p></div>
        <span class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700"><ShieldCheck class="h-4 w-4 text-sky-700" />{{ t('superAdministrator') }}</span>
      </div>

      <Card class="mt-7 p-5 sm:p-6">
        <div class="flex items-start gap-3"><span class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-sky-50 text-sky-700"><Landmark class="h-5 w-5" /></span><div class="min-w-0"><h2 class="font-semibold text-slate-900">{{ t('trustedInstitutions') }}</h2><p class="mt-1 text-sm leading-6 text-slate-600">{{ t('selectInstitutionFirst') }}</p></div></div>
        <div class="mt-5 max-w-xl"><Select v-model="selectedInstitution" :options="institutionOptions" :placeholder="t('selectInstitution')" :disabled="loading || !institutionOptions.length" /></div>
        <p v-if="!loading && !institutionOptions.length" class="mt-3 text-sm text-slate-500">{{ t('selectInstitutionFirst') }}</p>
      </Card>

      <div v-if="selectedInstitution" class="mt-6 grid gap-6 lg:grid-cols-[.9fr_1.1fr]">
        <Card class="p-5 sm:p-6"><div class="flex items-center gap-2"><UserRoundPlus class="h-5 w-5 text-sky-700" /><h2 class="font-semibold text-slate-900">{{ t('assignInstitutionAdministrator') }}</h2></div><p class="mt-2 text-sm leading-6 text-slate-600">{{ selectedInstitutionName }}</p><form class="mt-5 grid gap-4" @submit.prevent="assignAdministrator"><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('selectInstitutionAccount') }}<Select v-model="selectedAccount" :options="accountOptions" :placeholder="t('selectInstitutionAccount')" :disabled="loading || saving || !accountOptions.length" /></label><p v-if="!accounts.length && !loading" class="text-sm leading-6 text-slate-500">{{ t('noInstitutionAccounts') }}</p><Button type="submit" :disabled="saving || !selectedAccount"><UserRoundPlus class="mr-2 h-4 w-4" />{{ saving ? t('loading') : t('assignInstitutionAdministrator') }}</Button></form></Card>

        <Card class="overflow-hidden p-0"><div class="border-b border-slate-200 px-5 py-5 sm:px-6"><h2 class="font-semibold text-slate-900">{{ t('institutionAdministrators') }}</h2><p class="mt-1 text-sm text-slate-500">{{ selectedInstitutionName }} · {{ selectedInstitution }}</p></div><div v-if="selectedScopes.length" class="divide-y divide-slate-100"><div v-for="scope in selectedScopes" :key="scope.id" class="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6"><div><p class="font-medium text-slate-900">{{ scope.full_name }}</p><p class="mt-1 text-sm text-slate-500">{{ scope.username }}</p></div><Button type="button" size="sm" variant="outline" :disabled="saving" @click="removeAdministrator(scope)"><Trash2 class="mr-1.5 h-3.5 w-3.5" />{{ t('removeInstitutionAdministrator') }}</Button></div></div><p v-else class="p-8 text-center text-sm text-slate-500">{{ t('noUsers') }}</p></Card>
      </div>

      <p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p><p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
    </div>
  </DashboardLayout>
</template>
