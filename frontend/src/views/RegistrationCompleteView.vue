<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { CheckCircle2 } from 'lucide-vue-next'

import AuthLayout from '@/components/AuthLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const { t } = useI18n()

function enterWorkspace() {
  const role = auth.state.user?.roles.includes('mentor') ? 'mentor' : 'student'
  router.push(`/${role}`)
}
</script>

<template>
  <AuthLayout>
    <Card class="w-full p-8 text-center sm:p-10">
      <span class="mx-auto grid h-14 w-14 place-items-center rounded-full bg-emerald-100 text-emerald-700"><CheckCircle2 class="h-7 w-7" /></span>
      <h2 class="mt-6 text-2xl font-semibold tracking-tight text-slate-900">{{ t('registrationCompleted') }}</h2>
      <p class="mt-3 text-sm leading-6 text-slate-600">{{ t('registrationCompletedDescription') }}</p>
      <Button class="mt-7" type="button" size="lg" @click="enterWorkspace">{{ t('goToWorkspace') }}</Button>
    </Card>
  </AuthLayout>
</template>
