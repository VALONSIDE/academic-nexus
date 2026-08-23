<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import AuthLayout from '@/components/AuthLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/types/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { t } = useI18n()

const availableRoles: Role[] = ['student', 'mentor', 'admin']
const routeRole = route.params.role
const selectedRole = ref<Role>(availableRoles.includes(routeRole as Role) ? (routeRole as Role) : 'student')
const username = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)
const roleLabel = computed(() => t(selectedRole.value))

function selectRole(role: Role) {
  selectedRole.value = role
  error.value = ''
}

async function submit() {
  error.value = ''
  submitting.value = true
  try {
    const user = await auth.login({ username: username.value, password: password.value })
    const hasSelectedRole = selectedRole.value === 'admin'
      ? user.roles.some(role => ['admin', 'super_admin', 'institution_admin'].includes(role))
      : user.roles.includes(selectedRole.value)
    if (!hasSelectedRole) {
      auth.logout()
      error.value = t('roleMismatch')
      return
    }
    await router.push(`/${selectedRole.value}`)
  } catch {
    error.value = t('loginFailed')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthLayout>
    <Card class="w-full p-7 sm:p-8">
      <div class="mb-7">
        <p class="text-sm font-medium text-sky-700">{{ roleLabel }}</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{{ t('welcomeBack') }}</h2>
        <p class="mt-2 text-sm leading-6 text-slate-500">{{ t('loginDescription') }}</p>
      </div>

      <div class="mb-6">
        <p class="mb-2 text-sm font-medium text-slate-700">{{ t('selectIdentity') }}</p>
        <div class="grid grid-cols-3 rounded-lg bg-slate-100 p-1">
          <button
            v-for="role in availableRoles"
            :key="role"
            type="button"
            class="rounded-md px-2 py-2 text-xs font-medium transition sm:text-sm"
            :class="selectedRole === role ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'"
            @click="selectRole(role)"
          >{{ t(role) }}</button>
        </div>
      </div>

      <form class="space-y-4" autocomplete="off" data-lpignore="true" @submit.prevent="submit">
        <label class="grid gap-1.5 text-sm font-medium text-slate-700">
          {{ t('username') }}
          <Input v-model="username" name="academicnexus-login-username" type="text" autocomplete="off" data-lpignore="true" required />
        </label>
        <label class="grid gap-1.5 text-sm font-medium text-slate-700">
          {{ t('password') }}
          <Input v-model="password" name="academicnexus-login-password" type="password" autocomplete="new-password" data-lpignore="true" required />
        </label>
        <p v-if="error" class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{{ error }}</p>
        <Button class="w-full" type="submit" size="lg" :disabled="submitting">{{ submitting ? t('loading') : t('login') }}</Button>
      </form>

      <p v-if="selectedRole !== 'admin'" class="mt-6 text-center text-sm text-slate-500">
        {{ t('noAccount') }}
        <RouterLink to="/activate" class="font-medium text-sky-700 hover:text-sky-800">{{ t('activateAccount') }}</RouterLink>
      </p>
    </Card>
  </AuthLayout>
</template>
