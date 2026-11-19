<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Search, Settings2, Unlock, UsersRound } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import Switch from '@/components/ui/switch/Switch.vue'
import ToggleGroup from '@/components/ui/toggle-group/ToggleGroup.vue'
import { useAuthStore } from '@/stores/auth'
import type { AdminSelectionRecord, AdminSelectionUser, SelectionStatus } from '@/types/auth'

const auth = useAuthStore(); const { t } = useI18n()
const superAdmin = computed(() => auth.state.user?.roles.some(role => ['admin', 'super_admin'].includes(role)))
const role = ref<'student' | 'mentor'>('student')
const isOpen = ref(true); const capacity = ref(5); const choiceLimit = ref(1)
const users = ref<AdminSelectionUser[]>([]); const records = ref<AdminSelectionRecord[]>([])
const recordIds = ref<string[]>([]); const recordStatus = ref<SelectionStatus | ''>(''); const recordSearch = ref('')
const loading = ref(false); const message = ref(''); const error = ref('')
const exceptionsOnly = ref(false)
const exceptionUserIds = ref(new Set<string>())
const userSearch = ref('')
const roleOptions = computed(() => ['student', 'mentor'].map(value => ({ value, label: t(value) })))
const modeOptions = computed(() => [
  { value: 'manual', label: t('manualSelection') },
  { value: 'first_come', label: t('firstComeSelection') },
])
function hasException(item: AdminSelectionUser) {
  return item.is_exempt || item.choice_limit !== null || item.capacity !== null || item.selection_mode === 'first_come'
}
const visibleUsers = computed(() => users.value.filter(item => {
  const query = userSearch.value.trim().toLocaleLowerCase()
  const matches = !query || [item.full_name, item.username, item.institution_name_zh, item.college_name_zh]
    .some(field => field?.toLocaleLowerCase().includes(query))
  return item.role === role.value && matches && (!exceptionsOnly.value || exceptionUserIds.value.has(item.user_id))
}))
const statusLabels: Record<SelectionStatus, string> = { pending_student: 'selectedPending', pending_mentor: 'mentorInvitationPending', confirmed: 'selectionConfirmed', rejected: 'rejected', cancelled: 'cancelled' }
const statuses = Object.keys(statusLabels) as SelectionStatus[]

async function loadSettings() { if (!auth.state.token) return; const settings = await authApi.selectionSettings(auth.state.token); isOpen.value = settings.is_open; capacity.value = settings.default_capacity; choiceLimit.value = settings.default_student_choice_limit }
async function loadUsers() {
  if (!auth.state.token) return
  const currentRole = role.value
  const result = await authApi.adminSelectionUsers(auth.state.token, currentRole)
  if (currentRole === role.value) {
    users.value = result
    exceptionUserIds.value = new Set(result.filter(hasException).map(user => user.user_id))
  }
}
async function loadRecords() { if (!auth.state.token) return; const result = await authApi.adminSelectionRecords(auth.state.token, { selection_status: recordStatus.value || undefined, search: recordSearch.value.trim() || undefined }); records.value = result.items; recordIds.value = recordIds.value.filter((id) => result.items.some((item) => item.id === id)) }
async function load() { loading.value = true; error.value = ''; try { await Promise.all([loadSettings(), loadUsers(), loadRecords()]) } catch { error.value = t('updateFailed') } finally { loading.value = false } }
async function saveGlobal() { if (!auth.state.token) return; loading.value = true; try { await authApi.updateSelectionSettings(auth.state.token, { is_open: isOpen.value, default_capacity: capacity.value, default_student_choice_limit: choiceLimit.value }); message.value = t('selectionUpdated') } catch (exception) { error.value = exception instanceof ApiError && exception.code === 'selection_quota_below_usage' ? t('selectionQuotaBelowUsage') : t('updateFailed') } finally { loading.value = false } }
async function saveUser(user: AdminSelectionUser, useDefault = false) {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const settings = user.role === 'student'
      ? { choice_limit: user.choice_limit, is_exempt: user.is_exempt }
      : { capacity: user.capacity, is_exempt: user.is_exempt, selection_mode: user.selection_mode ?? undefined }
    const result = await authApi.updateAdminSelectionUser(auth.state.token, user.user_id, useDefault ? { use_default: true } : settings)
    users.value = users.value.map(item => item.user_id === result.user_id ? result : item)
    if (hasException(result)) exceptionUserIds.value.add(result.user_id)
    else exceptionUserIds.value.delete(result.user_id)
    message.value = t('selectionUpdated')
  } catch (exception) {
    error.value = exception instanceof ApiError && exception.code === 'selection_quota_below_usage'
      ? t('selectionQuotaBelowUsage') : t('updateFailed')
  } finally {
    loading.value = false
  }
}
async function releaseRecords(ids: string[]) {
  if (!auth.state.token || !ids.length) return
  const firstId = ids[0]
  if (!firstId || !window.confirm(`${t('releaseSelected')} (${ids.length})?`)) return
  loading.value = true
  try {
    if (ids.length === 1) await authApi.releaseAdminSelectionRecord(auth.state.token, firstId)
    else await authApi.releaseAdminSelectionRecords(auth.state.token, ids)
    recordIds.value = []
    await Promise.all([loadRecords(), loadUsers()])
    message.value = t('selectionUpdated')
  } catch { error.value = t('updateFailed') } finally { loading.value = false }
}
async function switchRole(value: string) {
  if (value !== 'student' && value !== 'mentor') return
  role.value = value
  loading.value = true
  error.value = ''
  try { await loadUsers() } catch { error.value = t('updateFailed') } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <DashboardLayout><div class="mx-auto w-full max-w-7xl"><p class="text-sm font-medium text-sky-700">{{ t('workspace') }}</p><h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900">{{ t('selectionManagement') }}</h1><p class="mt-3 leading-7 text-slate-600">{{ t('selectionIntro') }}</p>
    <p class="mt-2 text-sm text-slate-600">{{ t('selectionExceptionHint') }}</p><Card v-if="superAdmin" class="mt-8 p-6"><div class="flex items-center gap-3"><span class="grid h-10 w-10 place-items-center rounded-xl bg-slate-900 text-white"><Settings2 class="h-5 w-5" /></span><div><h2 class="font-semibold">{{ t('selectionManagement') }}</h2><p class="text-sm text-slate-500">{{ t('selectionCapacity') }}</p></div></div><div class="mt-7 grid gap-5 md:grid-cols-3"><label class="flex items-center gap-3 rounded-xl border border-slate-200 p-4"><input v-model="isOpen" type="checkbox" class="h-4 w-4" /><span class="font-medium">{{ t('selectionOpen') }}</span></label><label class="grid gap-2 text-sm font-medium"><span>{{ t('defaultMentorCapacity') }}</span><Input :model-value="String(capacity)" type="number" min="1" max="200" @update:model-value="capacity = Number($event)" /></label><label class="grid gap-2 text-sm font-medium"><span>{{ t('studentChoiceLimit') }}</span><Input :model-value="String(choiceLimit)" type="number" min="1" max="50" @update:model-value="choiceLimit = Number($event)" /></label></div><Button class="mt-6" :disabled="loading" @click="saveGlobal">{{ t('saveSelectionSettings') }}</Button></Card>
    <Card class="mt-6 overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 p-5">
        <div class="flex items-center gap-2">
          <UsersRound class="h-5 w-5 text-sky-700" />
          <h2 class="font-semibold">{{ t('selectionManagement') }}</h2>
        </div>
        <Input v-model="userSearch" type="search" class="max-w-64" :placeholder="t('searchUsersPlaceholder')" />
        <Switch v-model="exceptionsOnly" :label="t('exceptionEnabled')" />
        <ToggleGroup :model-value="role" :options="roleOptions" :label="t('selectionManagement')" :disabled="loading" @update:model-value="switchRole" />
      </div>
      <div v-if="loading" class="p-6 text-sm text-slate-500">{{ t('loading') }}</div>
      <div v-else class="divide-y divide-slate-100">
        <form v-for="user in visibleUsers" :key="user.user_id" class="grid items-start gap-4 p-5 lg:grid-cols-[minmax(0,1fr)_minmax(12rem,16rem)_auto]" @submit.prevent="saveUser(user)">
          <div class="min-w-0">
            <p class="font-medium">{{ user.full_name }}</p>
            <p class="mt-1 truncate text-sm text-slate-500">{{ user.username }} · {{ user.institution_name_zh }} · {{ user.college_name_zh }}</p>
            <p class="mt-2 text-xs leading-6 text-slate-600">
              {{ t('defaultSelectionLimit') }} {{ user.default_limit }} ·
              {{ t('effectiveSelectionLimit') }} {{ user.is_exempt ? t('unlimitedQuota') : user.effective_limit }} ·
              {{ t('pendingSelectionCount') }} {{ user.pending_count }} ·
              {{ t('confirmedSelectionCount') }} {{ user.confirmed_count }} ·
              {{ t('availableSlots') }} {{ user.available ?? t('unlimitedQuota') }}
            </p>
          </div>
          <div class="grid gap-3">
            <label v-if="user.role === 'student'" class="grid gap-1 text-sm">
              {{ t('studentChoiceLimit') }}
              <Input :model-value="user.choice_limit === null ? '' : String(user.choice_limit)" :placeholder="String(user.default_limit)" type="number" min="1" max="50" @update:model-value="user.choice_limit = $event === '' || $event == null ? null : Number($event)" />
            </label>
            <label v-else class="grid gap-1 text-sm">
              {{ t('selectionCapacity') }}
              <Input :model-value="user.capacity === null ? '' : String(user.capacity)" :placeholder="String(user.default_limit)" type="number" min="1" max="200" @update:model-value="user.capacity = $event === '' || $event == null ? null : Number($event)" />
            </label>
            <label v-if="user.role === 'mentor'" class="grid gap-1 text-sm">
              {{ t('selectionMode') }}
              <Select :model-value="user.selection_mode ?? 'manual'" :options="modeOptions" :aria-label="t('selectionMode')" @update:model-value="user.selection_mode = $event === 'first_come' ? 'first_come' : 'manual'" />
            </label>
            <Switch v-model="user.is_exempt" :label="t('exceptionEnabled')" />
          </div>
          <div class="flex flex-wrap gap-2 lg:pt-6">
            <Button type="submit" variant="outline" :disabled="loading">{{ t('save') }}</Button>
            <Button v-if="exceptionUserIds.has(user.user_id)" type="button" variant="ghost" :disabled="loading" @click="saveUser(user, true)">{{ t('standardRule') }}</Button>
          </div>
        </form>
        <p v-if="!visibleUsers.length" class="p-8 text-center text-sm text-slate-500">{{ t('noUsers') }}</p>
      </div>
    </Card>

    <Card class="mt-6 overflow-hidden"><div class="flex flex-col justify-between gap-4 border-b border-slate-200 p-5 lg:flex-row lg:items-center"><div class="flex items-center gap-2"><Unlock class="h-5 w-5 text-sky-700" /><h2 class="font-semibold">{{ t('selectionRecords') }}</h2></div><Button v-if="recordIds.length" variant="outline" :disabled="loading" @click="releaseRecords(recordIds)">{{ t('releaseSelected') }} ({{ recordIds.length }})</Button></div><form class="grid gap-3 border-b border-slate-100 p-4 md:grid-cols-[minmax(0,1fr)_12rem_auto]" @submit.prevent="loadRecords"><label class="relative"><Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><Input v-model="recordSearch" class="pl-9" :placeholder="t('searchUsersPlaceholder')" /></label><Select v-model="recordStatus" :options="[{value: '', label: t('all')}, ...Object.entries(statusLabels).map(([value, label]) => ({value, label: t(label)}))]" :aria-label="t('preRegistrationStatus')" /><Button type="submit" variant="outline">{{ t('search') }}</Button></form><div v-if="loading" class="p-8 text-center text-sm text-slate-500">{{ t('loading') }}</div><div v-else-if="!records.length" class="p-8 text-center text-sm text-slate-500">{{ t('selectionActivityEmpty') }}</div><div v-else class="divide-y divide-slate-100"><div v-for="record in records" :key="record.id" class="grid gap-3 p-5 md:grid-cols-[auto_minmax(0,1fr)_auto]"><input v-if="['pending_student', 'pending_mentor', 'confirmed'].includes(record.status)" v-model="recordIds" :value="record.id" type="checkbox" class="mt-1 h-4 w-4" /><div class="min-w-0"><p class="font-medium text-slate-900">{{ record.student_name }} <span class="text-slate-400">→</span> {{ record.mentor_name }} <span class="ml-2 rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{{ t(statusLabels[record.status]) }}</span></p><p class="mt-1 truncate text-sm text-slate-500">{{ record.student_username }} · {{ record.student_institution_name_zh }} · {{ record.student_college_name_zh }}</p><p class="mt-1 truncate text-sm text-slate-500">{{ record.mentor_username }} · {{ record.mentor_institution_name_zh }} · {{ record.mentor_college_name_zh }}</p></div><Button v-if="['pending_student', 'pending_mentor', 'confirmed'].includes(record.status)" size="sm" variant="ghost" :disabled="loading" @click="releaseRecords([record.id])">{{ t('releaseSelection') }}</Button></div></div></Card><p v-if="message" class="mt-5 text-sm text-emerald-700">{{ message }}</p><p v-if="error" class="mt-5 text-sm text-rose-700">{{ error }}</p>
  </div></DashboardLayout>
</template>
