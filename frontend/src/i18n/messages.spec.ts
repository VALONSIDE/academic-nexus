import { describe, expect, it } from 'vitest'

import { messages } from './messages'

describe('bilingual messages', () => {
  it('keeps the Chinese and English UI key sets identical', () => {
    expect(Object.keys(messages['zh-CN']).sort()).toEqual(Object.keys(messages['en-US']).sort())
  })

  it('contains Chinese and English strings for authentication', () => {
    expect(messages['zh-CN'].login).toBe('登录')
    expect(messages['en-US'].login).toBe('Sign in')
    expect(messages['zh-CN'].activateAccount).toBe('激活账户')
    expect(messages['en-US'].activateAccount).toBe('Activate account')
  })
})
