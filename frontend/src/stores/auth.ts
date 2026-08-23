import { computed, reactive, ref } from 'vue'

import { authApi } from '@/api/client'
import { i18n } from '@/i18n'
import type {
  ActivationPayload,
  AuthResponse,
  Locale,
  LoginPayload,
  MentorAcademicProfile,
  StudentAcademicProfile,
  User,
} from '@/types/auth'

const tokenKey = 'academicnexus.access-token'
const userKey = 'academicnexus.user'
const registrationKey = 'academicnexus.registration'

interface RegistrationSession {
  token: string
  role: 'student' | 'mentor'
}

function storedUser(): User | null {
  try {
    return JSON.parse(window.localStorage.getItem(userKey) || 'null') as User | null
  } catch {
    return null
  }
}

const state = reactive<{ token: string | null; user: User | null }>({
  token: window.localStorage.getItem(tokenKey),
  user: storedUser(),
})

function storedRegistration(): RegistrationSession | null {
  try {
    return JSON.parse(window.sessionStorage.getItem(registrationKey) || 'null') as RegistrationSession | null
  } catch {
    return null
  }
}

const registration = ref<RegistrationSession | null>(storedRegistration())

function persist(result: AuthResponse) {
  state.token = result.access_token
  state.user = result.user
  window.localStorage.setItem(tokenKey, result.access_token)
  window.localStorage.setItem(userKey, JSON.stringify(result.user))
  i18n.global.locale.value = result.user.preferred_locale
  window.localStorage.setItem('academicnexus.locale', result.user.preferred_locale)
  document.documentElement.lang = result.user.preferred_locale
}

export function useAuthStore() {
  const isAuthenticated = computed(() => Boolean(state.token && state.user))

  async function login(payload: LoginPayload) {
    const result = await authApi.login(payload)
    persist(result)
    return result.user
  }

  async function startActivation(payload: ActivationPayload) {
    const result = await authApi.activate(payload)
    registration.value = { token: result.registration_token, role: result.role }
    window.sessionStorage.setItem(registrationKey, JSON.stringify(registration.value))
    return registration.value
  }

  async function completeRegistration(
    role: 'student' | 'mentor',
    payload: StudentAcademicProfile | MentorAcademicProfile,
  ) {
    if (!registration.value || registration.value.role !== role) throw new Error('Registration session expired')
    const result = role === 'student'
      ? await authApi.completeStudentRegistration(registration.value.token, payload as StudentAcademicProfile)
      : await authApi.completeMentorRegistration(registration.value.token, payload as MentorAcademicProfile)
    persist(result)
    registration.value = null
    window.sessionStorage.removeItem(registrationKey)
    return result.user
  }

  async function refreshUser() {
    if (!state.token) return null
    try {
      state.user = await authApi.me(state.token)
      window.localStorage.setItem(userKey, JSON.stringify(state.user))
      return state.user
    } catch {
      logout()
      return null
    }
  }

  async function setLocale(locale: Locale) {
    if (!state.token || !state.user) return
    state.user = await authApi.updateLocale(state.token, locale)
    window.localStorage.setItem(userKey, JSON.stringify(state.user))
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    if (!state.token) throw new Error('Authentication required')
    const result = await authApi.changeOwnPassword(state.token, currentPassword, newPassword)
    persist(result)
    return result.user
  }

  function logout() {
    state.token = null
    state.user = null
    window.localStorage.removeItem(tokenKey)
    window.localStorage.removeItem(userKey)
    registration.value = null
    window.sessionStorage.removeItem(registrationKey)
  }

  return { state, registration, isAuthenticated, login, startActivation, completeRegistration, refreshUser, setLocale, changePassword, logout }
}
