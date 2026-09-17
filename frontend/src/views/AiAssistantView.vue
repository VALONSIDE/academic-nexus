<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { BotMessageSquare, Check, CircleGauge, Pencil, Plus, Radio, Save, Send, Sparkles, Trash2, Zap, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import ErrorDialog from '@/components/ErrorDialog.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { renderMarkdown } from '@/lib/markdown'
import { useAuthStore } from '@/stores/auth'
import type { AiConversation, AiConversationDetail, AiMessage, AiModelTier, AiQuota, AiResponseMode, AiTopic } from '@/types/auth'

const auth = useAuthStore()
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const conversations = ref<AiConversation[]>([])
const activeConversation = ref<AiConversationDetail | null>(null)
const quota = ref<AiQuota | null>(null)
const composer = ref('')
const newConversationTopic = ref<AiTopic>('academic_planning')
const selectedModelTier = ref<AiModelTier>('standard')
const responseMode = ref<AiResponseMode>('stream')
const loading = ref(false)
const sending = ref(false)
const renaming = ref(false)
const savingTitle = ref(false)
const deletingConversation = ref(false)
const renameTitle = ref('')
const streamedReply = ref('')
const error = ref('')
const errorDetails = ref<string[]>([])
const messagesPane = ref<HTMLElement | null>(null)

const DEFAULT_CONVERSATION_TITLE = 'New conversation'

const topics = computed<{ value: AiTopic; label: string }[]>(() => [
  { value: 'academic_planning', label: t('academicPlanning') },
  { value: 'mentor_consultation', label: t('mentorConsultation') },
  { value: 'learning_roadmap', label: t('learningRoadmap') },
  { value: 'selection_advisor', label: t('selectionAdvisor') },
])

const modelTiers = computed<{ value: AiModelTier; label: string; description: string; cost: number; icon: typeof Zap }[]>(() => [
  { value: 'light', label: t('aiModelLight'), description: t('aiModelLightDescription'), cost: 1, icon: Zap },
  { value: 'standard', label: t('aiModelStandard'), description: t('aiModelStandardDescription'), cost: 1, icon: CircleGauge },
  { value: 'expert', label: t('aiModelExpert'), description: t('aiModelExpertDescription'), cost: 2, icon: Sparkles },
])

const responseModes = computed<{ value: AiResponseMode; label: string; icon: typeof Radio }[]>(() => [
  { value: 'stream', label: t('aiResponseStream'), icon: Radio },
  { value: 'standard', label: t('aiResponseStandard'), icon: Check },
])

function errorMessage(exception: unknown): string {
  if (!(exception instanceof ApiError)) return t('aiRequestFailed')
  if (exception.code === 'user_daily_limit_reached') return t('aiUserLimitReached')
  if (exception.code === 'project_daily_limit_reached') return t('aiProjectLimitReached')
  if (exception.code === 'credit_balance_exhausted') return t('aiBalanceExhausted')
  if (exception.code === 'provider_not_configured') return t('aiUnavailable')
  return t('aiRequestFailed')
}

function quotaExceeded(exception: unknown): boolean {
  return exception instanceof ApiError && [
    'user_daily_limit_reached',
    'project_daily_limit_reached',
    'credit_balance_exhausted',
  ].includes(exception.code || '')
}

function displayConversationTitle(title: string): string {
  return title === DEFAULT_CONVERSATION_TITLE ? t('newConversation') : title
}

function formatConversationDate(value: string): string {
  return new Intl.DateTimeFormat(locale.value === 'en-US' ? 'en-US' : 'zh-CN', { dateStyle: 'medium' }).format(new Date(value))
}

function formatMessageTimestamp(value: string): string {
  return new Intl.DateTimeFormat(locale.value === 'en-US' ? 'en-US' : 'zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function subscriptionPlanLabel(plan: string): string {
  const keys: Record<string, string> = { basic: 'subscriptionPlanBasic', pro: 'subscriptionPlanPro', ultra: 'subscriptionPlanUltra', max: 'subscriptionPlanMax' }
  return t(keys[plan] || 'subscriptionPlanBasic')
}

async function scrollToBottom() {
  await nextTick()
  if (messagesPane.value) messagesPane.value.scrollTop = messagesPane.value.scrollHeight
}

async function loadWorkspace() {
  if (!auth.state.token) return
  loading.value = true
  error.value = ''
  errorDetails.value = []
  try {
    const [loadedQuota, loadedConversations] = await Promise.all([
      authApi.aiQuota(auth.state.token),
      authApi.aiConversations(auth.state.token),
    ])
    quota.value = loadedQuota
    conversations.value = loadedConversations
    const requestedTopic = route.query.topic
    const candidate = route.query.candidate
    if (requestedTopic === 'selection_advisor') {
      await createConversation('selection_advisor')
      if (typeof candidate === 'string' && candidate.trim()) composer.value = t('selectionAdvisorPrompt', { name: candidate })
      await router.replace({ query: {} })
    } else if (loadedConversations[0]) await selectConversation(loadedConversations[0].id)
  } catch (exception) {
    error.value = errorMessage(exception)
  } finally {
    loading.value = false
  }
}

async function selectConversation(conversationId: string) {
  if (!auth.state.token) return
  error.value = ''
  errorDetails.value = []
  renaming.value = false
  try {
    activeConversation.value = await authApi.aiConversation(auth.state.token, conversationId)
    await scrollToBottom()
  } catch (exception) {
    error.value = errorMessage(exception)
  }
}

async function createConversation(topic = newConversationTopic.value) {
  if (!auth.state.token) return
  error.value = ''
  errorDetails.value = []
  try {
    const conversation = await authApi.createAiConversation(auth.state.token, topic)
    conversations.value = [conversation, ...conversations.value]
    await selectConversation(conversation.id)
  } catch (exception) {
    error.value = errorMessage(exception)
  }
}

async function startRenaming(conversationId: string) {
  if (sending.value || savingTitle.value) return
  if (activeConversation.value?.id !== conversationId) await selectConversation(conversationId)
  if (activeConversation.value?.id !== conversationId || !activeConversation.value.messages.length) return
  renameTitle.value = activeConversation.value.title
  renaming.value = true
}

function cancelRenaming() {
  renaming.value = false
  renameTitle.value = ''
}

async function saveConversationTitle() {
  if (!auth.state.token || !activeConversation.value || savingTitle.value) return
  const title = renameTitle.value.trim()
  if (!title) return
  savingTitle.value = true
  error.value = ''
  try {
    const updated = await authApi.renameAiConversation(auth.state.token, activeConversation.value.id, title)
    activeConversation.value.title = updated.title
    const item = conversations.value.find(conversation => conversation.id === updated.id)
    if (item) item.title = updated.title
    cancelRenaming()
  } catch {
    error.value = t('updateFailed')
  } finally {
    savingTitle.value = false
  }
}

async function deleteConversation(conversationId: string) {
  if (!auth.state.token || sending.value || deletingConversation.value) return
  if (!conversations.value.some(conversation => conversation.id === conversationId)) return
  if (!window.confirm(t('deleteConversationConfirm'))) return
  const deletingActiveConversation = activeConversation.value?.id === conversationId
  deletingConversation.value = true
  error.value = ''
  try {
    await authApi.deleteAiConversation(auth.state.token, conversationId)
    conversations.value = conversations.value.filter(item => item.id !== conversationId)
    if (deletingActiveConversation) {
      activeConversation.value = null
      cancelRenaming()
      const next = conversations.value[0]
      if (next) await selectConversation(next.id)
    }
  } catch {
    error.value = t('deleteConversationFailed')
  } finally {
    deletingConversation.value = false
  }
}

function replaceOptimisticMessage(id: string, messages: AiMessage[]) {
  if (!activeConversation.value) return
  const index = activeConversation.value.messages.findIndex(message => message.id === id)
  if (index === -1) activeConversation.value.messages.push(...messages)
  else activeConversation.value.messages.splice(index, 1, ...messages)
}

async function refreshQuotaSafely() {
  if (!auth.state.token) return
  try {
    quota.value = await authApi.aiQuota(auth.state.token)
  } catch {
    // A quota refresh must not hide the original message request result.
  }
}

async function recoverCompletedStream(conversation: AiConversationDetail, content: string): Promise<boolean> {
  if (!auth.state.token || !streamedReply.value) return false
  try {
    const recovered = await authApi.aiConversation(auth.state.token, conversation.id)
    const lastUserMessage = recovered.messages[recovered.messages.length - 2]
    const lastAssistantMessage = recovered.messages[recovered.messages.length - 1]
    const persistedTurn = lastUserMessage?.role === 'user'
      && lastUserMessage.content === content
      && lastAssistantMessage?.role === 'assistant'
    if (!persistedTurn) return false

    if (activeConversation.value?.id === conversation.id) activeConversation.value = recovered
    const item = conversations.value.find(candidate => candidate.id === conversation.id)
    if (item) {
      item.title = recovered.title
      item.last_message_at = recovered.last_message_at
    }
    await refreshQuotaSafely()
    await scrollToBottom()
    return true
  } catch {
    return false
  }
}

async function send() {
  if (!auth.state.token || !activeConversation.value || !composer.value.trim() || sending.value) return
  const conversation = activeConversation.value
  const content = composer.value.trim()
  const requestedResponseMode = responseMode.value
  const optimisticId = `pending-${Date.now()}`
  const optimisticMessage: AiMessage = { id: optimisticId, role: 'user', content, created_at: new Date().toISOString() }
  conversation.messages.push(optimisticMessage)
  composer.value = ''
  streamedReply.value = ''
  sending.value = true
  error.value = ''
  errorDetails.value = []
  await scrollToBottom()
  try {
    const result = requestedResponseMode === 'stream'
      ? await authApi.sendAiMessageStream(auth.state.token, conversation.id, content, selectedModelTier.value, (text) => {
        streamedReply.value += text
        void scrollToBottom()
      })
      : await authApi.sendAiMessage(auth.state.token, conversation.id, content, { model_tier: selectedModelTier.value, response_mode: 'standard' })
    replaceOptimisticMessage(optimisticId, [result.user_message, result.assistant_message])
    quota.value = result.quota
    const item = conversations.value.find(candidate => candidate.id === conversation.id)
    if (conversation.title === DEFAULT_CONVERSATION_TITLE) conversation.title = content.slice(0, 80)
    if (item) {
      item.title = conversation.title
      item.last_message_at = result.assistant_message.created_at
    }
    await scrollToBottom()
  } catch (exception) {
    const recovered = requestedResponseMode === 'stream' && await recoverCompletedStream(conversation, content)
    if (!recovered) {
      conversation.messages = conversation.messages.filter(message => message.id !== optimisticId)
      composer.value = content
      error.value = errorMessage(exception)
      if (quotaExceeded(exception)) errorDetails.value = [error.value]
      await refreshQuotaSafely()
    }
  } finally {
    streamedReply.value = ''
    sending.value = false
  }
}

onMounted(loadWorkspace)
</script>

<template>
  <DashboardLayout>
    <div class="flex min-h-0 flex-col lg:h-[calc(100dvh-9.5rem)]">
      <div class="flex shrink-0 flex-col justify-between gap-4 xl:flex-row xl:items-end">
        <div><p class="text-sm font-medium text-sky-700">{{ t('workspace') }}</p><h1 class="mt-1 text-3xl font-semibold tracking-tight text-slate-900">{{ t('aiAssistant') }}</h1></div>
        <Card v-if="quota" class="grid shrink-0 grid-cols-3 divide-x divide-slate-100 px-1 py-2 shadow-sm"><div class="px-4 text-center"><p class="text-xs text-slate-500">{{ t('aiCycleUsage') }}</p><p class="mt-1 text-lg font-semibold">{{ quota.cycle_credits_used }}/{{ quota.cycle_credit_limit }}</p></div><div class="px-4 text-center"><p class="text-xs text-slate-500">{{ t('aiCycleRemaining') }}</p><p class="mt-1 text-lg font-semibold text-sky-700">{{ quota.credit_balance }}</p></div><div class="px-4 text-center"><p class="text-xs text-slate-500">{{ t('subscriptionPlan') }}</p><p class="mt-1 text-lg font-semibold">{{ subscriptionPlanLabel(quota.plan_code) }}</p></div></Card>
      </div>

      <div class="mt-5 grid min-h-[40rem] flex-1 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/20 lg:min-h-0 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <aside class="min-h-0 overflow-y-auto border-b border-slate-200 bg-slate-50/70 p-4 lg:border-r lg:border-b-0">
          <p class="px-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{{ t('aiConversation') }}</p>
          <form class="mt-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm" @submit.prevent="createConversation()">
            <label class="grid gap-1.5 text-xs font-medium text-slate-600">{{ t('conversationTopic') }}<Select v-model="newConversationTopic" :options="topics" class="h-9" /></label>
            <Button class="mt-3 w-full" type="submit"><Plus class="mr-2 h-4 w-4" />{{ t('createConversation') }}</Button>
          </form>
          <div v-if="conversations.length" class="mt-5 space-y-1">
            <div v-for="conversation in conversations" :key="conversation.id" class="group relative">
              <button type="button" class="w-full rounded-xl px-3 py-2.5 pr-20 text-left text-sm transition" :class="activeConversation?.id === conversation.id ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-700 hover:bg-slate-200/70'" @click="selectConversation(conversation.id)"><span class="block truncate font-medium">{{ displayConversationTitle(conversation.title) }}</span><span class="mt-1 flex items-center gap-1 truncate text-xs opacity-70"><span class="truncate">{{ t(conversation.topic) }}</span><span aria-hidden="true">·</span><time :datetime="conversation.last_message_at || conversation.created_at">{{ formatConversationDate(conversation.last_message_at || conversation.created_at) }}</time></span></button>
              <div class="absolute right-2 top-1/2 flex -translate-y-1/2 translate-x-1 gap-1 opacity-0 transition duration-150 group-hover:translate-x-0 group-hover:opacity-100 group-focus-within:translate-x-0 group-focus-within:opacity-100">
                <button v-if="conversation.last_message_at" type="button" class="grid h-7 w-7 place-items-center rounded-md bg-slate-950 text-white shadow-sm transition hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-500" :aria-label="t('renameConversation')" :title="t('renameConversation')" @click.stop="startRenaming(conversation.id)"><Pencil class="h-3.5 w-3.5" /></button>
                <button type="button" class="grid h-7 w-7 place-items-center rounded-md bg-rose-600 text-white shadow-sm transition hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-rose-400 disabled:cursor-not-allowed disabled:opacity-60" :disabled="sending || deletingConversation" :aria-label="t('deleteConversation')" :title="t('deleteConversation')" @click.stop="deleteConversation(conversation.id)"><Trash2 class="h-3.5 w-3.5" /></button>
              </div>
            </div>
          </div>
        </aside>

        <section class="flex min-h-0 flex-col">
          <template v-if="activeConversation">
            <header class="flex shrink-0 flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-3 sm:px-6"><span class="grid h-9 w-9 place-items-center rounded-xl bg-sky-100 text-sky-700"><BotMessageSquare class="h-5 w-5" /></span><div class="min-w-0 flex-1"><template v-if="renaming"><label class="sr-only" for="conversation-title">{{ t('conversationName') }}</label><input id="conversation-title" v-model="renameTitle" class="h-9 w-full max-w-md rounded-lg border border-slate-300 px-2 text-sm font-semibold text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100" type="text" maxlength="160" :aria-label="t('conversationName')" @keydown.enter.prevent="saveConversationTitle" @keydown.esc.prevent="cancelRenaming" /></template><h2 v-else class="truncate font-semibold text-slate-900">{{ displayConversationTitle(activeConversation.title) }}</h2><p class="text-xs text-slate-500">{{ t(activeConversation.topic) }} · {{ t('conversationStartedOn', { date: formatConversationDate(activeConversation.created_at) }) }}</p></div><div v-if="renaming" class="ml-auto flex items-center gap-2"><Button type="button" size="sm" :disabled="savingTitle || !renameTitle.trim()" @click="saveConversationTitle"><Save class="mr-1.5 h-3.5 w-3.5" />{{ t('save') }}</Button><Button type="button" variant="outline" size="sm" :disabled="savingTitle" :aria-label="t('cancel')" @click="cancelRenaming"><X class="h-3.5 w-3.5" /></Button></div></header>
            <div ref="messagesPane" class="min-h-0 flex-1 space-y-5 overflow-y-auto bg-gradient-to-b from-white to-slate-50/60 px-5 py-5 sm:px-8"><article v-for="message in activeConversation.messages" :key="message.id" class="flex" :class="message.role === 'user' ? 'justify-end' : 'justify-start'"><div class="max-w-[85%]"><div class="markdown-content rounded-2xl px-4 py-3 text-sm leading-7 shadow-sm" :class="message.role === 'user' ? 'rounded-br-md bg-slate-900 text-white' : 'rounded-bl-md border border-slate-200 bg-white text-slate-800'" v-html="renderMarkdown(message.content)" /><time class="mt-1 block text-xs text-slate-400" :class="message.role === 'user' ? 'text-right' : 'text-left'" :datetime="message.created_at">{{ formatMessageTimestamp(message.created_at) }}</time></div></article><article v-if="sending" class="flex justify-start"><div class="max-w-[85%] rounded-2xl rounded-bl-md border border-sky-100 bg-sky-50 px-4 py-3 text-sm leading-7 text-slate-700 shadow-sm"><div v-if="streamedReply" class="markdown-content" v-html="renderMarkdown(streamedReply)" /><div v-else class="flex items-center gap-2"><Sparkles class="h-4 w-4 animate-pulse text-sky-600" />{{ t('aiThinking') }}</div></div></article><div v-if="!activeConversation.messages.length && !sending" class="grid h-full min-h-48 place-items-center"><span class="grid h-11 w-11 place-items-center rounded-2xl bg-sky-100 text-sky-700"><BotMessageSquare class="h-5 w-5" /></span></div></div>
            <form class="shrink-0 border-t border-slate-200 bg-white p-3 sm:p-4" @submit.prevent="send"><div class="rounded-2xl border border-slate-200 bg-slate-50 p-2 focus-within:border-sky-500 focus-within:ring-2 focus-within:ring-sky-100"><div class="flex items-end gap-3"><textarea v-model="composer" class="min-h-12 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none" :placeholder="t('messagePlaceholder')" :disabled="sending" @keydown.enter.exact.prevent="send" /><Button type="submit" size="sm" :disabled="sending || !composer.trim()"><Send class="mr-1.5 h-3.5 w-3.5" />{{ t('sendMessage') }}</Button></div><div class="mt-2 flex flex-col gap-2 border-t border-slate-200 pt-2 xl:flex-row xl:items-center xl:justify-between"><div class="flex flex-wrap gap-1.5" :aria-label="t('aiModelDepth')"><button v-for="model in modelTiers" :key="model.value" type="button" class="inline-flex items-center gap-1.5 rounded-lg border px-2 py-1.5 text-xs transition" :class="selectedModelTier === model.value ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'" :title="model.description" :aria-pressed="selectedModelTier === model.value" @click="selectedModelTier = model.value"><component :is="model.icon" class="h-3.5 w-3.5" />{{ model.label }} · {{ t('aiCredits', { count: model.cost }) }}</button></div><div class="flex rounded-lg bg-white p-1 ring-1 ring-slate-200" :aria-label="t('aiResponseMode')"><button v-for="mode in responseModes" :key="mode.value" type="button" class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition" :class="responseMode === mode.value ? 'bg-slate-100 text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'" :aria-pressed="responseMode === mode.value" @click="responseMode = mode.value"><component :is="mode.icon" class="h-3.5 w-3.5" />{{ mode.label }}</button></div></div></div><p class="mt-2 text-xs leading-5 text-slate-500">{{ t('aiModelCostNote') }}</p></form>
          </template>
          <div v-else class="grid min-h-0 flex-1 place-items-center px-6 text-center"><div><span class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-sky-100 text-sky-700"><BotMessageSquare class="h-6 w-6" /></span><p class="mt-4 max-w-sm text-sm leading-6 text-slate-600">{{ loading ? t('loading') : t('selectConversation') }}</p></div></div>
        </section>
      </div>
      <p v-if="error" class="mt-4 shrink-0 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p><ErrorDialog v-if="errorDetails.length" :title="t('aiQuota')" :details="errorDetails" :close-label="t('close')" @close="errorDetails = []" />
    </div>
  </DashboardLayout>
</template>

<style>
.markdown-content h1, .markdown-content h2, .markdown-content h3 { margin: .65rem 0 .35rem; font-weight: 700; line-height: 1.45; }
.markdown-content p { margin: 0 0 .65rem; }.markdown-content p:last-child { margin-bottom: 0; }
.markdown-content ul, .markdown-content ol { margin: .4rem 0 .65rem 1.25rem; }.markdown-content ul { list-style: disc; }.markdown-content ol { list-style: decimal; }
.markdown-content code { border-radius: .3rem; background: rgb(15 23 42 / .1); padding: .1rem .3rem; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.markdown-content a { text-decoration: underline; }.markdown-content pre { margin: .65rem 0; overflow-x: auto; border-radius: .5rem; background: rgb(15 23 42 / .08); padding: .75rem; }.markdown-content pre code { background: transparent; padding: 0; }
.markdown-content blockquote { margin: .65rem 0; border-left: 3px solid rgb(14 165 233); padding-left: .75rem; color: rgb(71 85 105); }.markdown-content table { margin: .65rem 0; width: 100%; border-collapse: collapse; font-size: .85em; }.markdown-content th, .markdown-content td { border: 1px solid rgb(226 232 240); padding: .35rem .5rem; text-align: left; }
</style>
