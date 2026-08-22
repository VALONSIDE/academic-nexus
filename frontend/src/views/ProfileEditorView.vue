<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { authApi } from '@/api/client'
import AcademicPortraitForm from '@/components/AcademicPortraitForm.vue'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { MentorAcademicProfile, StudentAcademicProfile } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const role = computed<'student' | 'mentor'>(() => auth.state.user?.roles.includes('mentor') ? 'mentor' : 'student')
const profile = ref<StudentAcademicProfile | MentorAcademicProfile | null>(null)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const notice = ref('')

async function loadProfile() {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  try {
    const response = role.value === 'student'
      ? await authApi.studentProfile(auth.state.token)
      : await authApi.mentorProfile(auth.state.token)
    profile.value = response.data
  } catch {
    error.value = t('updateFailed')
  } finally {
    loading.value = false
  }
}

async function saveProfile(payload: StudentAcademicProfile | MentorAcademicProfile) {
  if (!auth.state.token) return
  submitting.value = true
  error.value = ''
  notice.value = ''
  try {
    const response = role.value === 'student'
      ? await authApi.updateStudentProfile(auth.state.token, payload as StudentAcademicProfile)
      : await authApi.updateMentorProfile(auth.state.token, payload as MentorAcademicProfile)
    profile.value = response.data
    notice.value = t('portraitSaved')
  } catch {
    error.value = t('updateFailed')
  } finally {
    submitting.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <DashboardLayout>
    <div class="max-w-3xl">
      <h1 class="text-3xl font-semibold tracking-tight text-slate-900">{{ t('academicPortrait') }}</h1>
      <p class="mt-3 leading-7 text-slate-600">{{ role === 'student' ? t('studentPortraitDescription') : t('mentorPortraitDescription') }}</p>
      <Card class="mt-7 p-6 sm:p-8">
        <p v-if="loading" class="text-sm text-slate-500">{{ t('loading') }}</p>
        <AcademicPortraitForm v-else :role="role" :initial-value="profile" :submitting="submitting" :submit-label="t('save')" @submit="saveProfile" />
        <p v-if="notice" class="mt-5 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{{ notice }}</p>
        <p v-if="error" class="mt-5 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{{ error }}</p>
      </Card>
    </div>
  </DashboardLayout>
</template>
