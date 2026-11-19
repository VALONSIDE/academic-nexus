import { beforeEach, expect, it, vi } from 'vitest'
import { ApiError, authApi } from '@/api/client'
import type { User, UserSubscription } from '@/types/auth'
import { useAuthStore } from './auth'

const user = { id: 'user-1', preferred_locale: 'zh-CN', roles: ['student'] } as User
const store = useAuthStore()

beforeEach(() => {
  vi.restoreAllMocks()
  store.logout()
  store.state.token = 'token'
  store.state.user = user
})

it('keeps the session on network or server failure', async () => {
  vi.spyOn(authApi, 'me').mockRejectedValue(new ApiError('Unavailable', [], undefined, 503))
  await store.refreshUser()
  expect(store.state.token).toBe('token')
  expect(store.state.user?.id).toBe(user.id)
})

it('clears an expired session', async () => {
  vi.spyOn(authApi, 'me').mockRejectedValue(new ApiError('Expired', [], undefined, 401))
  await store.refreshUser()
  expect(store.state.token).toBeNull()
  expect(store.state.user).toBeNull()
})

it('does not restore a user after logout while refresh is in flight', async () => {
  let resolve!: (value: User) => void
  vi.spyOn(authApi, 'me').mockReturnValue(new Promise<User>(done => { resolve = done }))
  const pending = store.refreshUser()
  store.logout()
  resolve(user)
  await pending
  expect(store.state.user).toBeNull()
  expect(localStorage.getItem('academicnexus.user')).toBeNull()
})

it('keeps the confirmed subscription plan while the next page fetches it', async () => {
  expect(store.subscriptionPlan.value).toBeNull()
  const getSubscription = vi.spyOn(authApi, 'subscription').mockResolvedValue({ plan_code: 'pro' } as UserSubscription)
  await store.refreshSubscriptionPlan()
  let resolve!: (value: UserSubscription) => void
  getSubscription.mockReturnValue(new Promise(done => { resolve = done }))
  const pending = useAuthStore().refreshSubscriptionPlan()
  expect(useAuthStore().subscriptionPlan.value).toBe('pro')
  store.setSubscriptionPlan('token', 'ultra')
  resolve({ plan_code: 'pro' } as UserSubscription)
  await pending
  expect(store.subscriptionPlan.value).toBe('ultra')
  store.logout()
  expect(store.subscriptionPlan.value).toBeNull()
})
