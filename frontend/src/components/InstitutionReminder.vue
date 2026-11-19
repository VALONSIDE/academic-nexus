<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Bell } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { authApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import Dialog from '@/components/ui/dialog/Dialog.vue'
import { useAuthStore } from '@/stores/auth'
import type { ReminderCategory } from '@/lib/workspace'

const props = defineProps<{ institutions: {value: string; label: string}[]; initialInstitution?: string; initialCategory?: ReminderCategory }>()
const { t } = useI18n()
const auth = useAuthStore()
const open = ref(false)
const institution = ref('')
const recipient = ref('')
const category = ref<ReminderCategory>('quota')
const recipients = ref<{id: string; name: string; username: string}[]>([])
const loading = ref(false)
const sending = ref(false)
const sent = ref(false)
const error = ref(false)
let requestCount = 0
const categories = computed(() => (['quota', 'allocation', 'issuance', 'delivery'] as const)
  .map(value => ({ value, label: t(`event_reminder_${value}`) })))

function start() {
  institution.value = props.institutions.some(item => item.value === props.initialInstitution)
    ? props.initialInstitution! : props.institutions[0]?.value || ''
  category.value = props.initialCategory || 'quota'
  sent.value = false
  open.value = true
}

watch([open, institution], async ([visible, school]) => {
  const request = ++requestCount
  recipients.value = []
  recipient.value = ''
  error.value = false
  if (!visible || !school || !auth.state.token) return
  loading.value = true
  try {
    const result = await authApi.institutionReminderRecipients(auth.state.token, school)
    if (request === requestCount) recipients.value = result
  } catch {
    if (request === requestCount) error.value = true
  } finally {
    if (request === requestCount) loading.value = false
  }
})

async function send() {
  if (!auth.state.token || !recipient.value) return
  sending.value = true
  error.value = false
  try {
    await authApi.sendInstitutionReminder(auth.state.token, institution.value, recipient.value, category.value)
    sent.value = true
    open.value = false
  } catch {
    error.value = true
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <Button variant="outline" :disabled="!institutions.length" @click="start"><Bell class="mr-2 size-4" />{{ t('notifyInstitutionAdmin') }}</Button>
    <span v-if="sent" class="text-sm text-emerald-700" role="status">{{ t('reminderSent') }}</span>
    <Dialog v-model:open="open" :title="t('notifyInstitutionAdmin')" :description="t('reminderDescription')">
      <form class="grid gap-4" @submit.prevent="send">
        <label class="grid gap-2 text-sm font-medium">{{ t('institution') }}<Select v-model="institution" :options="institutions" :disabled="sending" /></label>
        <label class="grid gap-2 text-sm font-medium">{{ t('institutionAdministrator') }}<Select v-model="recipient" :disabled="loading || sending || !recipients.length" :options="recipients.map(user => ({value: user.id, label: user.name + ' · ' + user.username}))" :placeholder="t('selectRecipient')" /></label>
        <p v-if="!loading && !error && !recipients.length" class="text-sm text-slate-500">{{ t('noInstitutionRecipients') }}</p>
        <label class="grid gap-2 text-sm font-medium">{{ t('reminderCategory') }}<Select v-model="category" :options="categories" :disabled="sending" /></label>
        <p v-if="error" class="text-sm text-rose-700" role="alert">{{ t('updateFailed') }}</p>
        <Button class="justify-self-end" :disabled="sending || !recipient" type="submit">{{ t('sendReminder') }}</Button>
      </form>
    </Dialog>
  </div>
</template>
