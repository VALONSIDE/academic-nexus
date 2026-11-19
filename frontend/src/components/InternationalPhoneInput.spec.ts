import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import { i18n } from '@/i18n'
import InternationalPhoneInput from './InternationalPhoneInput.vue'

describe('International phone input', () => {
  it('retains incomplete input as invalid and accepts a valid international number', async () => {
    const wrapper = mount(InternationalPhoneInput, { global: { plugins: [i18n] } })
    const input = wrapper.find('input[type="tel"]')
    await input.setValue('1')
    expect(wrapper.emitted('valid')?.slice(-1)[0]).toEqual([false])
    expect(wrapper.emitted('update:modelValue')?.slice(-1)[0]?.[0]).not.toBe('')
    await input.setValue('+1 202 555 0123')
    expect(wrapper.emitted('valid')?.slice(-1)[0]).toEqual([true])
    expect(wrapper.emitted('update:modelValue')?.slice(-1)[0]).toEqual(['+12025550123'])
    await input.setValue('')
    expect(wrapper.emitted('valid')?.slice(-1)[0]).toEqual([true])
  })

  it('uses local flag assets rather than regional indicator characters', () => {
    const wrapper = mount(InternationalPhoneInput, { global: { plugins: [i18n] } })
    expect(wrapper.find('.fi-cn').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('🇨🇳')
  })
})
