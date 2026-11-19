<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { mailto, type PublicContact, type ContactChannel } from '@/lib/contacts'
const props = defineProps<{ userId: string; draft?: string; allowAi?: boolean }>()
const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const data = ref<PublicContact | null>(null)
const busy = ref(false)
const loading = ref(true)
const notice = ref('')
async function load() {
  if (!auth.state.token) return null
  loading.value = true
  try { data.value = await authApi.contact(auth.state.token, props.userId); return data.value }
  catch { data.value = null; notice.value = t('contactUnavailable'); return null }
  finally { loading.value = false }
}
async function act(channel: ContactChannel, draft = false) {
  busy.value = true; notice.value = ''
  try {
    const current = await load()
    const value = current?.[channel === 'sms' ? 'phone' : channel]
    if (!value) { notice.value = t('contactNotShared'); return }
    if (draft) {
      const role = auth.state.user?.roles.includes('student') ? 'student' : 'mentor'
      await router.push({ path: `/${role}/assistant`, query: { contact: props.userId, channel } })
    } else if (channel === 'email') window.location.assign(mailto(value, props.draft))
    else { await navigator.clipboard.writeText(value); notice.value = t('copied') }
  } catch { notice.value = t('actionFailed') } finally { busy.value = false }
}
watch(() => props.userId, () => { data.value = null; void load() }, { immediate: true })
onMounted(() => window.addEventListener('focus', load))
onUnmounted(() => window.removeEventListener('focus', load))
</script>
<template>
  <section class="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
    <h3 class="font-semibold text-slate-900">{{ t('sameSchoolContact') }}<span v-if="data" class="ml-2 text-sm font-normal">{{ data.full_name }}</span></h3>
    <div v-for="item in [{channel: 'email' as const, field: 'email' as const, label: 'email', action: 'sendEmail', ai: 'draftEmail'}, {channel: 'sms' as const, field: 'phone' as const, label: 'contactPhone', action: 'copyPhone', ai: 'draftSms'}, {channel: 'wechat' as const, field: 'wechat' as const, label: 'wechatId', action: 'copyWechat', ai: 'draftWechat'}]" :key="item.channel" class="mt-4 flex flex-wrap items-center gap-2">
      <div class="min-w-0 flex-1"><p class="text-xs text-slate-500">{{ t(item.label) }}</p><p class="break-all text-sm">{{ loading && !data ? t('loading') : data?.[item.field] || t('contactNotShared') }}</p></div>
      <Button size="sm" variant="outline" :disabled="busy || !data?.[item.field]" @click="act(item.channel)">{{ t(item.action) }}</Button>
      <Button v-if="allowAi" size="sm" variant="outline" :disabled="busy || !data?.[item.field]" @click="act(item.channel, true)">{{ t(item.ai) }}</Button>
    </div>
    <p v-if="notice" class="mt-3 text-xs text-sky-800" role="status">{{ notice }}</p>
    <p class="mt-3 text-xs leading-5 text-slate-500">{{ t('mailClientHint') }}</p>
  </section>
</template>
