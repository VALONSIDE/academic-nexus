<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Search, UserCog } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { authApi } from '@/api/client'
import AcademicPortraitForm from '@/components/AcademicPortraitForm.vue'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'
import type { AdminSelectionUser, ManagedUser, MentorAcademicProfile, StudentAcademicProfile } from '@/types/auth'

const props = defineProps<{ role: 'student' | 'mentor' }>()
const auth = useAuthStore()
const { t } = useI18n()
const users = ref<ManagedUser[]>([])
const selected = ref<ManagedUser | null>(null)
const selectedIds = ref<string[]>([])
const search = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const password = ref('')
const selectionConfig = ref<AdminSelectionUser | null>(null)
const selectionLimit = ref<number | null>(null)
const selectionExempt = ref(false)
const basic = reactive({ full_name: '', phone: '', is_active: true })

const title = computed(() => props.role === 'student' ? t('studentManagement') : t('mentorManagement'))
const selectedProfile = computed(() => selected.value?.profile || null)
const isScopedAdministrator = computed(() => {
  const roles = auth.state.user?.roles || []
  return roles.includes('institution_admin') && !roles.includes('admin') && !roles.includes('super_admin')
})

function applySelected(user: ManagedUser) {
  selected.value = user
  basic.full_name = user.full_name
  basic.phone = user.phone || ''
  basic.is_active = user.is_active
  password.value = ''
  error.value = ''
  notice.value = ''
  void loadSelectionConfig(user)
}

async function loadSelectionConfig(user: ManagedUser) {
  if (!auth.state.token) return
  try {
    const values = await authApi.adminSelectionUsers(auth.state.token, props.role)
    selectionConfig.value = values.find((item) => item.user_id === user.id) || null
    selectionLimit.value = props.role === 'student' ? selectionConfig.value?.choice_limit ?? null : selectionConfig.value?.capacity ?? null
    selectionExempt.value = selectionConfig.value?.is_exempt ?? false
  } catch { selectionConfig.value = null }
}

async function saveSelectionConfig() {
  if (!auth.state.token || !selected.value) return
  saving.value = true
  try {
    const result = await authApi.updateAdminSelectionUser(auth.state.token, selected.value.id, props.role === 'student'
      ? { choice_limit: selectionLimit.value || undefined, is_exempt: selectionExempt.value }
      : { capacity: selectionLimit.value || undefined, is_exempt: selectionExempt.value })
    selectionConfig.value = result
    notice.value = t('selectionUpdated')
  } catch { error.value = t('updateFailed') } finally { saving.value = false }
}

async function resetSelectionConfig() {
  if (!auth.state.token || !selected.value) return
  saving.value = true
  try {
    const result = await authApi.updateAdminSelectionUser(auth.state.token, selected.value.id, { use_default: true })
    selectionConfig.value = result
    selectionLimit.value = null
    selectionExempt.value = false
    notice.value = t('selectionUpdated')
  } catch { error.value = t('updateFailed') } finally { saving.value = false }
}

function replaceUser(user: ManagedUser) {
  users.value = users.value.map(item => item.id === user.id ? user : item)
  if (selected.value?.id === user.id) applySelected(user)
}

async function loadUsers() {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  try {
    const result = await authApi.managedUsers(auth.state.token, props.role, search.value)
    users.value = result.items
    if (selected.value) {
      const refreshed = result.items.find(item => item.id === selected.value?.id)
      if (refreshed) applySelected(refreshed)
      else selected.value = null
    }
  } catch {
    error.value = t('updateFailed')
  } finally {
    loading.value = false
  }
}

async function batchSetActive(isActive: boolean) {
  if (!auth.state.token || !selectedIds.value.length) return
  saving.value = true
  error.value = ''
  try {
    await authApi.updateManagedUsersStatus(auth.state.token, selectedIds.value, isActive)
    selectedIds.value = []
    await loadUsers()
    notice.value = t('userSaved')
  } catch { error.value = t('updateFailed') } finally { saving.value = false }
}

async function saveBasic() {
  if (!auth.state.token || !selected.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await authApi.updateManagedUser(auth.state.token, selected.value.id, { ...basic })
    replaceUser(result)
    notice.value = t('userSaved')
  } catch {
    error.value = t('updateFailed')
  } finally {
    saving.value = false
  }
}

async function savePortrait(payload: StudentAcademicProfile | MentorAcademicProfile) {
  if (!auth.state.token || !selected.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = props.role === 'student'
      ? await authApi.updateManagedUser(auth.state.token, selected.value.id, { student_profile: payload as StudentAcademicProfile })
      : await authApi.updateManagedUser(auth.state.token, selected.value.id, { mentor_profile: payload as MentorAcademicProfile })
    replaceUser(result)
    notice.value = t('userSaved')
  } catch {
    error.value = t('updateFailed')
  } finally {
    saving.value = false
  }
}

async function resetPassword() {
  if (!auth.state.token || !selected.value || !password.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await authApi.resetManagedUserPassword(auth.state.token, selected.value.id, password.value)
    password.value = ''
    notice.value = t('passwordResetSaved')
  } catch {
    error.value = t('updateFailed')
  } finally {
    saving.value = false
  }
}

onMounted(loadUsers)
watch(() => props.role, () => {
  selected.value = null
  selectedIds.value = []
  search.value = ''
  void loadUsers()
})
</script>

<template>
  <DashboardLayout>
    <div>
      <h1 class="text-3xl font-semibold tracking-tight text-slate-900">{{ title }}</h1>
      <p class="mt-3 leading-7 text-slate-600">{{ isScopedAdministrator ? t('institutionScopedManagementDescription') : t('managementDescription') }}</p>

      <Card class="mt-7 overflow-hidden">
        <form class="flex gap-2 border-b border-slate-200 p-4" @submit.prevent="loadUsers">
          <Input v-model="search" class="min-w-0 flex-1" :placeholder="t('searchUsersPlaceholder')" type="search" />
          <Button class="whitespace-nowrap" type="submit" variant="outline" :disabled="loading"><Search class="mr-2 h-4 w-4" />{{ t('search') }}</Button>
        </form>
        <div v-if="loading" class="p-5 text-sm text-slate-500">{{ t('loading') }}</div>
        <div v-else-if="users.length === 0" class="p-8 text-center text-sm text-slate-500">{{ t('noUsers') }}</div>
        <div v-if="selectedIds.length" class="flex flex-wrap items-center gap-2 border-b border-slate-100 bg-sky-50 px-5 py-3"><span class="mr-auto text-sm font-medium text-sky-900">{{ t('selectedCount', { count: selectedIds.length }) }}</span><Button size="sm" variant="outline" :disabled="saving" @click="batchSetActive(true)">{{ t('batchEnable') }}</Button><Button size="sm" variant="outline" :disabled="saving" @click="batchSetActive(false)">{{ t('batchDisable') }}</Button></div>
        <div class="divide-y divide-slate-100">
          <button v-for="user in users" :key="user.id" type="button" class="grid w-full grid-cols-[minmax(0,1fr)_auto] gap-4 px-5 py-4 text-left transition hover:bg-slate-50" :class="selected?.id === user.id ? 'bg-sky-50' : ''" @click="applySelected(user)">
            <span class="min-w-0">
              <span class="flex items-center gap-3"><input v-model="selectedIds" :value="user.id" type="checkbox" class="h-4 w-4 shrink-0" @click.stop /><span class="block truncate font-medium text-slate-900">{{ user.full_name }}</span></span>
              <span class="mt-1 block truncate text-sm text-slate-500">{{ user.username }} · {{ user.academic_id }}</span>
            </span>
            <span class="flex items-center gap-2 text-xs font-medium">
              <span class="rounded-full px-2 py-1" :class="user.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'">{{ user.is_active ? t('active') : t('disabled') }}</span>
              <span class="rounded-full px-2 py-1" :class="user.profile_completed ? 'bg-sky-100 text-sky-800' : 'bg-amber-100 text-amber-800'">{{ user.profile_completed ? t('complete') : t('incomplete') }}</span>
            </span>
          </button>
        </div>
      </Card>

      <div v-if="selected" class="mt-8 grid gap-6 xl:grid-cols-2">
        <Card class="p-6">
          <div class="flex items-center gap-2">
            <UserCog class="h-5 w-5 text-sky-700" />
            <h2 class="font-semibold text-slate-900">{{ t('basicInformation') }}</h2>
          </div>
          <dl class="mt-5 grid grid-cols-2 gap-4 text-sm">
            <div><dt class="text-slate-500">{{ t('username') }}</dt><dd class="mt-1 break-all font-medium text-slate-900">{{ selected.username }}</dd></div>
            <div><dt class="text-slate-500">{{ t('academicIdentity') }}</dt><dd class="mt-1 font-medium text-slate-900">{{ selected.academic_id }}</dd></div>
            <div><dt class="text-slate-500">{{ t('schoolChineseName') }}</dt><dd class="mt-1 font-medium text-slate-900">{{ selected.institution_name_zh || selected.institution_abbr }}</dd></div>
            <div><dt class="text-slate-500">{{ t('collegeChineseName') }}</dt><dd class="mt-1 font-medium text-slate-900">{{ selected.college_name_zh || '—' }}</dd></div>
            <div><dt class="text-slate-500">{{ t('profileStatus') }}</dt><dd class="mt-1 font-medium text-slate-900">{{ selected.profile_completed ? t('complete') : t('incomplete') }}</dd></div>
          </dl>
          <form class="mt-6 space-y-4 border-t border-slate-100 pt-6" @submit.prevent="saveBasic">
            <label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('fullName') }}<Input v-model="basic.full_name" required /></label>
            <label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('contactPhone') }}<Input v-model="basic.phone" type="tel" /></label>
            <label class="flex items-center gap-2 text-sm font-medium text-slate-700"><input v-model="basic.is_active" type="checkbox" class="h-4 w-4 rounded border-slate-300" />{{ basic.is_active ? t('active') : t('disabled') }}</label>
            <Button type="submit" :disabled="saving">{{ saving ? t('loading') : t('save') }}</Button>
          </form>

          <form v-if="selectionConfig" class="mt-7 space-y-3 border-t border-slate-100 pt-6" @submit.prevent="saveSelectionConfig">
            <h3 class="font-semibold text-slate-900">{{ t('mutualSelection') }}</h3>
            <label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ props.role === 'student' ? t('studentChoiceLimit') : t('selectionCapacity') }}<Input :model-value="selectionLimit === null ? '' : String(selectionLimit)" type="number" min="1" :max="props.role === 'student' ? 50 : 200" @update:model-value="selectionLimit = $event ? Number($event) : null" /></label>
            <label class="flex items-center gap-2 text-sm font-medium text-slate-700"><input v-model="selectionExempt" type="checkbox" class="h-4 w-4 rounded border-slate-300" />{{ t('exceptionEnabled') }}</label>
            <div class="flex flex-wrap gap-2"><Button type="submit" variant="outline" :disabled="saving">{{ saving ? t('loading') : t('save') }}</Button><Button v-if="selectionExempt || selectionLimit !== null" type="button" variant="ghost" :disabled="saving" @click="resetSelectionConfig">{{ t('standardRule') }}</Button></div>
          </form>
          <form class="mt-7 space-y-3 border-t border-slate-100 pt-6" @submit.prevent="resetPassword">
            <h3 class="font-semibold text-slate-900">{{ t('resetPassword') }}</h3>
            <p class="text-sm leading-6 text-slate-600">{{ t('passwordResetDescription') }}</p>
            <label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('newPassword') }}<Input v-model="password" type="password" minlength="12" autocomplete="new-password" required /></label>
            <Button type="submit" variant="outline" :disabled="saving || !password">{{ saving ? t('loading') : t('resetPassword') }}</Button>
          </form>
        </Card>

        <Card class="p-6">
          <h2 class="font-semibold text-slate-900">{{ t('academicPortrait') }}</h2>
          <AcademicPortraitForm :role="role" :initial-value="selectedProfile" :submitting="saving" :submit-label="t('save')" @submit="savePortrait" />
        </Card>
      </div>

      <p v-if="notice" class="mt-6 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{{ notice }}</p>
      <p v-if="error" class="mt-6 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{{ error }}</p>
    </div>
  </DashboardLayout>
</template>
