<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import InternationalPhoneInput from '@/components/InternationalPhoneInput.vue'
import { Input } from '@/components/ui/input'
import Switch from '@/components/ui/switch/Switch.vue'
import type { ContactForm } from '@/lib/contacts'
const model = defineModel<ContactForm>({ required: true })
withDefaults(defineProps<{ required?: boolean }>(), { required: true })
const emit = defineEmits<{ valid: [boolean] }>()
const { t } = useI18n()
</script>
<template>
  <div class="grid gap-5">
    <div class="grid gap-2"><label class="text-sm font-medium">{{ t('contactPhone') }} <span class="font-normal text-slate-400">{{ t('optional') }}</span></label><InternationalPhoneInput v-model="model.phone" @valid="emit('valid', $event)" /><Switch v-model="model.share_phone" :label="t('sharePhone')" /></div>
    <div class="grid gap-2"><label class="grid gap-2 text-sm font-medium">{{ t('email') }}<Input v-model="model.email" type="email" autocomplete="email" maxlength="320" :required="required" /></label><Switch v-model="model.share_email" :label="t('shareEmail')" /></div>
    <div class="grid gap-2"><label class="grid gap-2 text-sm font-medium">{{ t('wechatId') }}<Input v-model="model.wechat" autocomplete="off" maxlength="64" pattern="[A-Za-z0-9_-]{3,64}" :required="required" :placeholder="t('wechatPlaceholder')" /></label><Switch v-model="model.share_wechat" :label="t('shareWechat')" /></div>
    <p class="text-xs leading-6 text-slate-500">{{ t('contactPrivacyHint') }}</p>
  </div>
</template>
