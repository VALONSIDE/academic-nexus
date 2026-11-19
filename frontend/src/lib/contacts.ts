export interface ContactForm {
  phone: string
  email: string
  wechat: string
  share_email: boolean
  share_phone: boolean
  share_wechat: boolean
}
export interface PublicContact {
  user_id: string
  full_name: string
  email: string | null
  phone: string | null
  wechat: string | null
  email_visible: boolean
  phone_visible: boolean
  wechat_visible: boolean
}
export type ContactChannel = 'email' | 'sms' | 'wechat'
export function emptyContacts(): ContactForm {
  return { phone: '', email: '', wechat: '', share_email: false, share_phone: false, share_wechat: false }
}
export function contactError(contact: ContactForm, required: boolean): string | null {
  if ((required || contact.email.trim()) && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact.email.trim())) return 'invalidEmailAddress'
  if ((required || contact.wechat.trim()) && !/^[A-Za-z0-9_-]{3,64}$/.test(contact.wechat.trim())) return 'invalidWechat'
  return null
}
export function mailto(email: string, content = ''): string {
  const lines = content.split('\n')
  const subject = lines[0]?.match(/^(?:Subject|主题)[：:]\s*(.*)$/i)?.[1] || ''
  const body = subject ? lines.slice(1).join('\n').trim() : content
  return `mailto:${encodeURIComponent(email).replace(/%40/gi, '@')}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}
