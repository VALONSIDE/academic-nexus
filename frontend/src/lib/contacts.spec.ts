import { describe, expect, it } from 'vitest'
import { contactError, emptyContacts, mailto } from './contacts'
describe('Contact validation and email drafts', () => {
  it('requires email and WeChat for academic accounts', () => {
    const value = emptyContacts()
    expect(contactError(value, true)).toBe('invalidEmailAddress')
    value.email = 'person@school.edu'
    expect(contactError(value, true)).toBe('invalidWechat')
    value.wechat = 'real_wechat_id'
    expect(contactError(value, true)).toBeNull()
    expect(contactError(emptyContacts(), false)).toBeNull()
  })
  it('encodes generated content as one subject and body, never extra mail headers', () => {
    const uri = mailto('person@school.edu', 'Subject: Hello & bcc=attacker@example.com\n\nBody # ? &')
    const url = new URL(uri)
    expect(url.pathname).toBe('person@school.edu')
    expect(url.searchParams.get('subject')).toBe('Hello & bcc=attacker@example.com')
    expect(url.searchParams.get('body')).toBe('Body # ? &')
    expect(url.searchParams.has('bcc')).toBe(false)
  })
})
