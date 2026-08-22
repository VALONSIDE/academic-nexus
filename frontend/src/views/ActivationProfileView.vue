<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import AcademicPortraitForm from '@/components/AcademicPortraitForm.vue'
import AuthLayout from '@/components/AuthLayout.vue'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { MentorAcademicProfile, StudentAcademicProfile } from '@/types/auth'

const router = useRouter()
const auth = useAuthStore()
const { t } = useI18n()
const error = ref('')
const submitting = ref(false)
const role = computed(() => auth.registration.value?.role)

onMounted(() => {
  if (!role.value) router.replace('/activate')
})

async function submit(payload: StudentAcademicProfile | MentorAcademicProfile) {
  if (!role.value) return
  error.value = ''
  submitting.value = true
  try {
    await auth.completeRegistration(role.value, payload)
    await router.push('/registration-complete')
  } catch {
    error.value = t('profileFailed')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthLayout>
    <Card class="w-full p-7 sm:p-8">
      <template v-if="role">
        <div class="mb-7">
          <p class="text-sm font-medium text-sky-700">{{ t('registrationStepTwo') }}</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{{ t('profileCompletionTitle') }}</h2>
          <p class="mt-2 text-sm leading-6 text-slate-500">{{ t('profileCompletionDescription') }}</p>
        </div>
        <AcademicPortraitForm :role="role" :submitting="submitting" :submit-label="t('submitProfileAndFinish')" @submit="submit" />
        <p v-if="error" class="mt-5 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{{ error }}</p>
      </template>
      <template v-else>
        <h2 class="text-xl font-semibold text-slate-900">{{ t('profileCompletionTitle') }}</h2>
        <p class="mt-3 text-sm leading-6 text-slate-600">{{ t('registrationSessionMissing') }}</p>
      </template>
    </Card>
  </AuthLayout>
</template>
