<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import AuthLayout from '@/components/AuthLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { i18n } from '@/i18n'
import { useAuthStore } from '@/stores/auth'
import type { Locale } from '@/types/auth'

const router = useRouter()
const auth = useAuthStore()
const { t } = useI18n()

const username = ref('')
const fullName = ref('')
const academicId = ref('')
const accessKey = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function submit() {
  error.value = ''
  submitting.value = true
  try {
    await auth.startActivation({
      username: username.value,
      full_name: fullName.value,
      academic_id: academicId.value,
      access_key: accessKey.value,
      password: password.value,
      preferred_locale: i18n.global.locale.value as Locale,
    })
    await router.push('/activate/profile')
  } catch {
    error.value = t('registerFailed')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthLayout>
    <Card class="w-full p-7 sm:p-8">
      <div class="mb-7">
        <p class="text-sm font-medium text-sky-700">{{ t('registrationStepOne') }}</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{{ t('createAccount') }}</h2>
        <p class="mt-2 text-sm leading-6 text-slate-500">{{ t('registerDescription') }}</p>
        <p class="mt-3 rounded-lg bg-sky-50 px-3 py-2 text-xs leading-5 text-sky-900">{{ t('activationFields') }}</p>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <label class="grid gap-1.5 text-sm font-medium text-slate-700">
          {{ t('accountName') }}
          <Input v-model="username" type="text" autocomplete="username" required placeholder="CUC_S20240001" />
        </label>
        <label class="grid gap-1.5 text-sm font-medium text-slate-700">
          {{ t('fullName') }}
          <Input v-model="fullName" type="text" autocomplete="name" required />
        </label>
        <label class="grid gap-1.5 text-sm font-medium text-slate-700">
          {{ t('academicId') }}
          <Input v-model="academicId" type="text" required />
        </label>
        <label class="grid gap-1.5 text-sm font-medium text-slate-700">
          {{ t('accessKey') }}
          <Input v-model="accessKey" type="text" required placeholder="1234-ABCD-5678-9012" class="uppercase" />
        </label>
        <label class="grid gap-1.5 text-sm font-medium text-slate-700">
          {{ t('password') }}
          <Input v-model="password" type="password" autocomplete="new-password" minlength="12" required />
          <span class="font-normal text-slate-400">{{ t('passwordHint') }}</span>
        </label>
        <p v-if="error" class="whitespace-pre-line rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{{ error }}</p>
        <Button class="w-full" type="submit" size="lg" :disabled="submitting">{{ submitting ? t('loading') : t('continue') }}</Button>
      </form>

      <p class="mt-4 text-xs leading-5 text-slate-500">{{ t('secureNotice') }}</p>
      <p class="mt-4 text-center text-sm text-slate-500">
        {{ t('haveAccount') }}
        <RouterLink to="/login" class="font-medium text-sky-700 hover:text-sky-800">{{ t('login') }}</RouterLink>
      </p>
    </Card>
  </AuthLayout>
</template>
