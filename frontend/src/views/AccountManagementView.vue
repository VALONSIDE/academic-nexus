<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { BookUser, KeyRound, Mail, Phone, ShieldCheck, Sparkles, UserRound, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, authApi } from '@/api/client'
import AcademicPortraitForm from '@/components/AcademicPortraitForm.vue'
import AiQuotaSummary from '@/components/AiQuotaSummary.vue'
import DashboardLayout from '@/components/DashboardLayout.vue'
import InternationalPhoneInput from '@/components/InternationalPhoneInput.vue'
import MentorStorageQuotaSummary from '@/components/MentorStorageQuotaSummary.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'
import type { MentorAcademicProfile, Role, StudentAcademicProfile } from '@/types/auth'

type Panel = 'contact' | 'password' | 'portrait' | 'quota' | null

const auth = useAuthStore()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const academicRole = computed<'student' | 'mentor' | null>(() => {
  const roles = auth.state.user?.roles || []
  if (roles.includes('mentor')) return 'mentor'
  if (roles.includes('student')) return 'student'
  return null
})
const accountRole = computed<Role>(() => {
  const roles = auth.state.user?.roles || []
  if (roles.some(role => ['admin', 'super_admin', 'institution_admin'].includes(role))) return 'admin'
  return academicRole.value || 'student'
})
const hasPortrait = computed(() => academicRole.value !== null)
const activePanel = ref<Panel>(null)
const profile = ref<StudentAcademicProfile | MentorAcademicProfile | null>(null)
const contactPhone = ref('')
const contactEmail = ref('')
const phoneValid = ref(true)
const currentPassword = ref('')
const newPassword = ref('')
const confirmation = ref('')
const loadingProfile = ref(false)
const savingProfile = ref(false)
const savingContact = ref(false)
const changingPassword = ref(false)
const notice = ref('')
const error = ref('')

watch(() => [auth.state.user?.phone, auth.state.user?.email], ([phone, email]) => {
  contactPhone.value = phone || ''
  contactEmail.value = email || ''
}, { immediate: true })

function openPanel(panel: Exclude<Panel, null>) {
  activePanel.value = panel
  void router.replace({ query: { ...route.query, panel } })
}

function closePanel() {
  activePanel.value = null
  const query = { ...route.query }
  delete query.panel
  void router.replace({ query })
}

watch(() => route.query.panel, (panel) => {
  activePanel.value = panel === 'contact' || panel === 'password' || panel === 'portrait' || panel === 'quota' ? panel : null
}, { immediate: true })

async function loadProfile() {
  if (!auth.state.token || !academicRole.value) return
  loadingProfile.value = true
  try {
    profile.value = (academicRole.value === 'student'
      ? await authApi.studentProfile(auth.state.token)
      : await authApi.mentorProfile(auth.state.token)).data
  } catch {
    error.value = t('updateFailed')
  } finally {
    loadingProfile.value = false
  }
}

async function saveProfile(payload: StudentAcademicProfile | MentorAcademicProfile) {
  if (!auth.state.token || !academicRole.value) return
  savingProfile.value = true
  error.value = ''
  try {
    profile.value = (academicRole.value === 'student'
      ? await authApi.updateStudentProfile(auth.state.token, payload as StudentAcademicProfile)
      : await authApi.updateMentorProfile(auth.state.token, payload as MentorAcademicProfile)).data
    notice.value = t('portraitSaved')
    closePanel()
  } catch {
    error.value = t('updateFailed')
  } finally {
    savingProfile.value = false
  }
}

async function saveContact() {
  if (contactPhone.value && !phoneValid.value) {
    error.value = t('invalidInternationalPhone')
    return
  }
  savingContact.value = true
  error.value = ''
  try {
    await auth.updateContact({ phone: contactPhone.value, email: contactEmail.value })
    notice.value = t('userSaved')
    closePanel()
  } catch (exception) {
    error.value = exception instanceof ApiError && exception.code === 'email_already_in_use'
      ? t('emailAlreadyInUse')
      : t('updateFailed')
  } finally {
    savingContact.value = false
  }
}

async function changePassword() {
  if (!auth.state.token) return
  error.value = ''
  if (newPassword.value !== confirmation.value) {
    error.value = t('passwordMismatch')
    return
  }
  changingPassword.value = true
  try {
    await auth.changePassword(currentPassword.value, newPassword.value)
    currentPassword.value = ''
    newPassword.value = ''
    confirmation.value = ''
    notice.value = t('passwordChanged')
    closePanel()
  } catch (exception) {
    error.value = exception instanceof ApiError && exception.code === 'current_password_incorrect'
      ? t('currentPasswordIncorrect')
      : t('updateFailed')
  } finally {
    changingPassword.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <DashboardLayout>
    <div class="mx-auto w-full max-w-6xl">
      <div class="flex items-start gap-4">
        <span class="grid h-12 w-12 place-items-center rounded-2xl bg-slate-900 text-white"><UserRound class="h-6 w-6" /></span>
        <div><p class="text-sm font-medium text-sky-700">{{ auth.state.user?.username }}</p><h1 class="mt-1 text-3xl font-semibold tracking-tight text-slate-900">{{ t('accountManagement') }}</h1><p class="mt-2 leading-7 text-slate-600">{{ t('accountManagementDescription') }}</p></div>
      </div>

      <Card class="mt-8 p-6">
        <div class="flex items-center gap-2"><ShieldCheck class="h-5 w-5 text-sky-700" /><h2 class="font-semibold text-slate-900">{{ t('accountSettings') }}</h2></div>
        <dl class="mt-5 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><dt class="text-slate-500">{{ t('fullName') }}</dt><dd class="mt-1 font-medium">{{ auth.state.user?.full_name }}</dd></div>
          <div><dt class="text-slate-500">{{ t('accountName') }}</dt><dd class="mt-1 font-medium">{{ auth.state.user?.username }}</dd></div>
          <div><dt class="text-slate-500">{{ t('selectIdentity') }}</dt><dd class="mt-1 font-medium">{{ t(accountRole) }}</dd></div>
          <div><dt class="text-slate-500">{{ t('language') }}</dt><dd class="mt-1 font-medium">{{ auth.state.user?.preferred_locale === 'zh-CN' ? t('languageChinese') : t('languageEnglish') }}</dd></div>
        </dl>
      </Card>

      <div class="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <button type="button" class="rounded-2xl border border-slate-200 bg-white p-6 text-left transition hover:border-sky-300 hover:shadow-sm" @click="openPanel('contact')"><span class="flex gap-2"><Phone class="h-6 w-6 text-sky-700" /><Mail class="h-6 w-6 text-sky-700" /></span><h2 class="mt-4 font-semibold">{{ t('contactInformation') }}</h2><p class="mt-2 text-sm leading-6 text-slate-600">{{ t('contactInformationDescription') }}</p></button>
        <button type="button" class="rounded-2xl border border-slate-200 bg-white p-6 text-left transition hover:border-sky-300 hover:shadow-sm" @click="openPanel('password')"><KeyRound class="h-6 w-6 text-sky-700" /><h2 class="mt-4 font-semibold">{{ t('changePassword') }}</h2><p class="mt-2 text-sm leading-6 text-slate-600">{{ t('passwordHint') }}</p></button>
        <button v-if="hasPortrait" type="button" class="rounded-2xl border border-slate-200 bg-white p-6 text-left transition hover:border-sky-300 hover:shadow-sm" @click="openPanel('portrait')"><BookUser class="h-6 w-6 text-sky-700" /><h2 class="mt-4 font-semibold">{{ t('managePortrait') }}</h2><p class="mt-2 text-sm leading-6 text-slate-600">{{ t('academicPortrait') }}</p></button>
        <button v-if="hasPortrait" type="button" class="rounded-2xl border border-slate-200 bg-white p-6 text-left transition hover:border-sky-300 hover:shadow-sm" @click="openPanel('quota')"><Sparkles class="h-6 w-6 text-sky-700" /><h2 class="mt-4 font-semibold">{{ t('personalQuota') }}</h2><p class="mt-2 text-sm leading-6 text-slate-600">{{ t('aiQuotaNote') }}</p></button>
        <MentorStorageQuotaSummary v-if="academicRole === 'mentor'" />
      </div>

      <p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p>
      <p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>

      <div v-if="activePanel" class="fixed inset-0 z-50 grid place-items-center bg-slate-950/35 p-4" @click.self="closePanel">
        <Card class="max-h-[90vh] w-full max-w-3xl overflow-y-auto p-6">
          <div class="flex items-center justify-between gap-4"><h2 class="text-xl font-semibold">{{ activePanel === 'contact' ? t('contactInformation') : activePanel === 'password' ? t('changePassword') : activePanel === 'portrait' ? t('managePortrait') : t('personalQuota') }}</h2><Button variant="ghost" size="icon" @click="closePanel"><X class="h-4 w-4" /></Button></div>
          <form v-if="activePanel === 'contact'" class="mt-6 grid gap-5" @submit.prevent="saveContact"><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('contactPhone') }} <span class="font-normal text-slate-400">{{ t('optional') }}</span><InternationalPhoneInput v-model="contactPhone" @valid="phoneValid = $event" /></label><label class="grid gap-1.5 text-sm font-medium text-slate-700">{{ t('email') }} <span class="font-normal text-slate-400">{{ t('optional') }}</span><Input v-model="contactEmail" type="email" autocomplete="email" maxlength="320" /></label><Button class="w-fit" type="submit" :disabled="savingContact">{{ savingContact ? t('loading') : t('save') }}</Button></form>
          <form v-else-if="activePanel === 'password'" class="mt-6 grid gap-4" @submit.prevent="changePassword"><label class="grid gap-1.5 text-sm font-medium">{{ t('currentPassword') }}<Input v-model="currentPassword" type="password" autocomplete="current-password" required /></label><label class="grid gap-1.5 text-sm font-medium">{{ t('newPassword') }}<Input v-model="newPassword" type="password" minlength="12" autocomplete="new-password" required /></label><label class="grid gap-1.5 text-sm font-medium">{{ t('confirmPassword') }}<Input v-model="confirmation" type="password" minlength="12" autocomplete="new-password" required /></label><Button class="w-fit" type="submit" :disabled="changingPassword">{{ changingPassword ? t('loading') : t('changePassword') }}</Button></form>
          <div v-else-if="activePanel === 'portrait' && academicRole"><div v-if="loadingProfile" class="py-10 text-sm text-slate-500">{{ t('loading') }}</div><AcademicPortraitForm v-else-if="profile" class="mt-6" :role="academicRole" :initial-value="profile" :submitting="savingProfile" :submit-label="t('save')" @submit="saveProfile" /></div>
          <AiQuotaSummary v-else class="mt-6" />
        </Card>
      </div>
    </div>
  </DashboardLayout>
</template>
