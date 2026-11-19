<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import 'flag-icons/css/flag-icons.min.css'
import { AsYouType, getCountries, getCountryCallingCode, parsePhoneNumberFromString, type CountryCode } from 'libphonenumber-js/max'
import { useI18n } from 'vue-i18n'

import { Input } from '@/components/ui/input'
import { Select, type SelectOption } from '@/components/ui/select'

const model = defineModel<string>({ default: '' })
const emit = defineEmits<{ valid: [value: boolean] }>()
const props = withDefaults(defineProps<{
  disabled?: boolean
}>(), {
  disabled: false,
})

const { locale, t } = useI18n()
const country = ref<CountryCode>('CN')
const display = ref('')
const valid = ref(true)
let lastEmitted: string | null = null

const countryOptions = computed<SelectOption[]>(() => {
  const names = typeof Intl.DisplayNames === 'function'
    ? new Intl.DisplayNames([locale.value], { type: 'region' })
    : null
  return getCountries()
    .map(code => ({
      value: code,
      label: `${names?.of(code) || code} (+${getCountryCallingCode(code)})`,
      iconClass: `fi fi-${code.toLowerCase()}`,
    }))
    .sort((left, right) => left.label.localeCompare(right.label, locale.value))
})

function setValidity(value: boolean) {
  valid.value = value
  emit('valid', value)
}

function syncFromModel(value: string) {
  if (!value) {
    display.value = ''
    setValidity(true)
    return
  }
  const parsed = parsePhoneNumberFromString(value, country.value)
  if (parsed) {
    if (parsed.country) country.value = parsed.country
    display.value = parsed.formatNational()
    setValidity(parsed.isValid())
    if (parsed.isValid() && model.value !== parsed.number) { lastEmitted = parsed.number; model.value = parsed.number }
  } else {
    display.value = value
    setValidity(false)
  }
}

function formatInput(value: string | undefined) {
  const formatter = new AsYouType(country.value)
  display.value = formatter.input(value || '')
  const number = formatter.getNumber()
  lastEmitted = number?.number || display.value
  model.value = lastEmitted
  setValidity(!display.value || Boolean(number?.isValid()))
}

function changeCountry(next: string) {
  if (next === country.value) return
  const previous = country.value
  const parsed = parsePhoneNumberFromString(model.value || display.value, previous)
  const nationalNumber = parsed?.nationalNumber || display.value.replace(/\D/g, '')
  country.value = next as CountryCode
  if (nationalNumber) formatInput(nationalNumber)
}

watch(model, (value) => { if (value !== lastEmitted) syncFromModel(value) }, { immediate: true })
</script>

<template>
  <div>
    <div class="grid gap-3">
      <Select :model-value="country" :options="countryOptions" :disabled="props.disabled" @update:model-value="changeCountry" />
      <Input
        :model-value="display"
        type="tel"
        inputmode="tel"
        autocomplete="tel-national"
        :disabled="props.disabled"
        :aria-invalid="!valid"
        @update:model-value="formatInput"
      />
    </div>
    <p v-if="!valid" class="mt-1.5 text-xs text-rose-700">{{ t('invalidInternationalPhone') }}</p>
  </div>
</template>
