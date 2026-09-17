import { beforeEach, expect, it, vi } from 'vitest'
import { ApiError, authApi } from '@/api/client'
import type { User } from '@/types/auth'
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
