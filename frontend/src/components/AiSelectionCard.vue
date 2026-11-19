<script setup lang="ts">
import { ref } from 'vue'
import { ArrowRight, CheckCircle2, UsersRound } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { ApiError, authApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'
import type { AiActionCard } from '@/lib/workspace'

const props = defineProps<{ card: AiActionCard; conversationId: string; messageId: string; workspace: 'student' | 'mentor' }>()
const emit = defineEmits<{ completed: [AiActionCard] }>()
const auth = useAuthStore()
const { t } = useI18n()
const busy = ref(false)
const error = ref('')
async function execute() {
  if (!auth.state.token || busy.value) return
  busy.value = true
  error.value = ''
  try {
    emit('completed', await authApi.runAiAction(auth.state.token, props.conversationId, props.messageId))
  } catch (exception) {
    error.value = exception instanceof ApiError && exception.status === 409 ? t('aiCardStale') : t('selectionOperationFailed')
  } finally { busy.value = false }
}
</script>

<template>
  <section class="mt-3 rounded-xl border border-sky-200 bg-white p-4 shadow-sm">
    <div class="flex items-start gap-3">
      <span class="grid size-9 shrink-0 place-items-center rounded-lg bg-sky-50 text-sky-700"><UsersRound class="size-4" /></span>
      <div><p class="text-xs font-medium text-sky-700">{{ t('mutualSelection') }}</p><h3 class="mt-1 font-semibold">{{ card.target_name }}</h3></div>
    </div>
    <p v-if="card.state === 'completed'" class="mt-3 flex items-center gap-2 text-sm text-emerald-700" role="status"><CheckCircle2 class="size-4" />{{ t(card.result_status === 'confirmed' ? 'selectionConfirmed' : 'aiCardSubmitted') }}</p>
    <p v-else class="mt-3 text-sm text-slate-600">{{ t('aiCardReview') }}</p>
    <p v-if="error" class="mt-3 text-sm text-rose-700" role="alert">{{ error }}</p>
    <div class="mt-3 flex flex-wrap items-center gap-3">
      <Button v-if="card.state === 'ready'" size="sm" :disabled="busy" @click="execute">{{ t(busy ? 'loading' : `aiAction_${card.action}`) }}<ArrowRight class="ml-2 size-4" /></Button>
      <RouterLink :to="{path: `/${workspace}/matches`, query: {candidate: card.target_id}}" class="text-sm font-medium text-sky-700">{{ t('viewDetails') }}</RouterLink>
    </div>
  </section>
</template>
