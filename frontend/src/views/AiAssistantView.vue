<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { BotMessageSquare, Plus, Send, Sparkles } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import ErrorDialog from '@/components/ErrorDialog.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { AiConversation, AiConversationDetail, AiQuota, AiTopic } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const conversations = ref<AiConversation[]>([])
const activeConversation = ref<AiConversationDetail | null>(null)
const quota = ref<AiQuota | null>(null)
const composer = ref('')
const loading = ref(false)
const sending = ref(false)
const error = ref('')
const errorDetails = ref<string[]>([])
const messagesPane = ref<HTMLElement | null>(null)

const topics = computed<{ value: AiTopic; label: string }[]>(() => [
  { value: 'academic_planning', label: t('academicPlanning') },
  { value: 'mentor_consultation', label: t('mentorConsultation') },
  { value: 'learning_roadmap', label: t('learningRoadmap') },
  { value: 'selection_advisor', label: t('selectionAdvisor') },
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

function inlineMarkdown(source: string): string {
  return source
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
}

function renderMarkdown(source: string): string {
  const lines = source.replace(/\r\n?/g, '\n').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').split('\n')
  const output: string[] = []
  let index = 0
  const at = (position: number) => lines[position] ?? ''
  const isSpecial = (line: string) => /^(#{1,3}\s+|```|&gt;\s?|[-*+]\s+|\d+\.\s+|\|)/.test(line)
  while (index < lines.length) {
    const line = at(index)
    if (!line.trim()) { index += 1; continue }
    if (line.startsWith('```')) {
      const code: string[] = []; index += 1
      while (index < lines.length && !at(index).startsWith('```')) { code.push(at(index)); index += 1 }
      if (index < lines.length) index += 1
      output.push(`<pre><code>${code.join('\n')}</code></pre>`); continue
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) { const level = heading[1] ?? '#'; const content = heading[2] ?? ''; output.push(`<h${level.length}>${inlineMarkdown(content)}</h${level.length}>`); index += 1; continue }
    if (/^([-*_])\1\1+$/.test(line.trim())) { output.push('<hr>'); index += 1; continue }
    if (line.startsWith('&gt;')) {
      const quote: string[] = []
      while (index < lines.length && at(index).startsWith('&gt;')) { quote.push(at(index).replace(/^&gt;\s?/, '')); index += 1 }
      output.push(`<blockquote>${inlineMarkdown(quote.join('<br>'))}</blockquote>`); continue
    }
    const unordered = line.match(/^[-*+]\s+(.+)$/)
    const ordered = line.match(/^\d+\.\s+(.+)$/)
    if (unordered || ordered) {
      const tag = unordered ? 'ul' : 'ol'; const entries: string[] = []
      while (index < lines.length) { const match = at(index).match(unordered ? /^[-*+]\s+(.+)$/ : /^\d+\.\s+(.+)$/); if (!match) break; entries.push(`<li>${inlineMarkdown(match[1] ?? '')}</li>`); index += 1 }
      output.push(`<${tag}>${entries.join('')}</${tag}>`); continue
    }
    if (line.startsWith('|') && line.endsWith('|')) {
      const rows: string[][] = []
      while (index < lines.length && at(index).startsWith('|') && at(index).endsWith('|')) { const cells = at(index).slice(1, -1).split('|').map((cell) => cell.trim()); if (!cells.every((cell) => /^:?-{3,}:?$/.test(cell))) rows.push(cells); index += 1 }
      if (rows.length) { const header = rows[0] ?? []; const body = rows.slice(1); output.push(`<table><thead><tr>${header.map((cell) => `<th>${inlineMarkdown(cell)}</th>`).join('')}</tr></thead><tbody>${body.map((row) => `<tr>${row.map((cell) => `<td>${inlineMarkdown(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table>`) }
      continue
    }
    const paragraph: string[] = [line]; index += 1
    while (index < lines.length && at(index).trim() && !isSpecial(at(index))) { paragraph.push(at(index)); index += 1 }
    output.push(`<p>${inlineMarkdown(paragraph.join('<br>'))}</p>`)
  }
  return output.join('')
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
  try {
    activeConversation.value = await authApi.aiConversation(auth.state.token, conversationId)
    await scrollToBottom()
  } catch (exception) {
    error.value = errorMessage(exception)
  }
}

async function createConversation(topic: AiTopic) {
  if (!auth.state.token) return
  error.value = ''
  errorDetails.value = []
  try {
    // 将首个会话名称交给当前界面语言，避免中文界面出现英文默认名称。
    const conversation = await authApi.createAiConversation(auth.state.token, topic, t(topic))
    conversations.value = [conversation, ...conversations.value]
    await selectConversation(conversation.id)
  } catch (exception) {
    error.value = errorMessage(exception)
  }
}

async function send() {
  if (!auth.state.token || !activeConversation.value || !composer.value.trim() || sending.value) return
  sending.value = true
  error.value = ''
  errorDetails.value = []
  const content = composer.value.trim()
  composer.value = ''
  try {
    const result = await authApi.sendAiMessage(auth.state.token, activeConversation.value.id, content)
    activeConversation.value.messages.push(result.user_message, result.assistant_message)
    quota.value = result.quota
    const item = conversations.value.find(conversation => conversation.id === activeConversation.value?.id)
    if (activeConversation.value.title === 'New conversation') {
      activeConversation.value.title = content.slice(0, 80)
    }
    if (item) {
      item.title = activeConversation.value.title
      item.last_message_at = result.assistant_message.created_at
    }
    await scrollToBottom()
  } catch (exception) {
    composer.value = content
    error.value = errorMessage(exception)
    if (quotaExceeded(exception)) errorDetails.value = [error.value]
    if (auth.state.token) quota.value = await authApi.aiQuota(auth.state.token)
  } finally {
    sending.value = false
  }
}

onMounted(loadWorkspace)
</script>

<template>
  <DashboardLayout>
    <div class="min-h-[calc(100vh-9rem)]">
      <div class="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
        <div>
          <p class="text-sm font-medium text-sky-700">{{ t('workspace') }}</p>
          <h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900">{{ t('aiAssistant') }}</h1>
          <p class="mt-3 max-w-3xl leading-7 text-slate-600">{{ t('aiAssistantDescription') }}</p>
        </div>
        <Card v-if="quota" class="grid grid-cols-3 divide-x divide-slate-100 px-2 py-3 text-center shadow-none">
          <div class="px-4"><p class="text-xs text-slate-500">{{ t('aiDailyUsage') }}</p><p class="mt-1 text-lg font-semibold">{{ quota.daily_used }}/{{ quota.daily_limit }}</p></div>
          <div class="px-4"><p class="text-xs text-slate-500">{{ t('aiDailyRemaining') }}</p><p class="mt-1 text-lg font-semibold text-sky-700">{{ quota.daily_remaining }}</p></div>
          <div class="px-4"><p class="text-xs text-slate-500">{{ t('aiCreditBalance') }}</p><p class="mt-1 text-lg font-semibold">{{ quota.credit_balance }}</p></div>
        </Card>
      </div>

      <div class="mt-7 grid min-h-[38rem] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/25 lg:grid-cols-[19rem_minmax(0,1fr)]">
        <aside class="border-b border-slate-200 bg-slate-50/70 p-4 lg:border-r lg:border-b-0">
          <p class="px-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{{ t('aiConversation') }}</p>
          <div class="mt-3 grid gap-2">
            <Button v-for="topic in topics" :key="topic.value" variant="outline" type="button" class="justify-start" @click="createConversation(topic.value)"><Plus class="mr-2 h-4 w-4" />{{ topic.label }}</Button>
          </div>
          <div class="mt-6 space-y-1">
            <button v-for="conversation in conversations" :key="conversation.id" type="button" class="w-full rounded-xl px-3 py-2.5 text-left text-sm transition" :class="activeConversation?.id === conversation.id ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-700 hover:bg-slate-200/70'" @click="selectConversation(conversation.id)">
              <span class="block truncate font-medium">{{ conversation.title }}</span>
              <span class="mt-1 block text-xs opacity-70">{{ t(conversation.topic) }}</span>
            </button>
          </div>
        </aside>

        <section class="flex min-h-0 flex-col">
          <template v-if="activeConversation">
            <header class="flex items-center gap-3 border-b border-slate-100 px-6 py-4"><span class="grid h-9 w-9 place-items-center rounded-xl bg-sky-100 text-sky-700"><BotMessageSquare class="h-5 w-5" /></span><div><h2 class="font-semibold text-slate-900">{{ activeConversation.title }}</h2><p class="text-xs text-slate-500">{{ t(activeConversation.topic) }}</p></div></header>
            <div ref="messagesPane" class="flex-1 space-y-5 overflow-y-auto bg-gradient-to-b from-white to-slate-50/60 px-5 py-6 sm:px-8">
              <article v-for="message in activeConversation.messages" :key="message.id" class="flex" :class="message.role === 'user' ? 'justify-end' : 'justify-start'">
                <div class="markdown-content max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-7 shadow-sm" :class="message.role === 'user' ? 'rounded-br-md bg-slate-900 text-white' : 'rounded-bl-md border border-slate-200 bg-white text-slate-800'" v-html="renderMarkdown(message.content)" />
              </article>
              <div v-if="sending" class="flex items-center gap-2 text-sm text-slate-500"><Sparkles class="h-4 w-4 animate-pulse text-sky-600" />{{ t('loading') }}</div>
            </div>
            <form class="border-t border-slate-200 bg-white p-4 sm:p-5" @submit.prevent="send">
              <div class="flex items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-2 focus-within:border-sky-500 focus-within:ring-2 focus-within:ring-sky-100">
                <textarea v-model="composer" class="min-h-12 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none" :placeholder="t('messagePlaceholder')" :disabled="sending" @keydown.enter.exact.prevent="send" />
                <Button type="submit" size="sm" :disabled="sending || !composer.trim()"><Send class="mr-1.5 h-3.5 w-3.5" />{{ t('sendMessage') }}</Button>
              </div>
              <p class="mt-2 text-xs leading-5 text-slate-500">{{ t('aiQuotaNote') }}</p>
            </form>
          </template>
          <div v-else class="grid flex-1 place-items-center px-6 text-center">
            <div><span class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-sky-100 text-sky-700"><BotMessageSquare class="h-6 w-6" /></span><p class="mt-4 max-w-sm text-sm leading-6 text-slate-600">{{ loading ? t('loading') : t('selectConversation') }}</p></div>
          </div>
        </section>
      </div>
      <p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
      <ErrorDialog v-if="errorDetails.length" :title="t('aiQuota')" :details="errorDetails" :close-label="t('close')" @close="errorDetails = []" />
    </div>
  </DashboardLayout>
</template>

<style>
.markdown-content h1, .markdown-content h2, .markdown-content h3 { margin: .65rem 0 .35rem; font-weight: 700; line-height: 1.45; }
.markdown-content p { margin: 0 0 .65rem; }
.markdown-content p:last-child { margin-bottom: 0; }
.markdown-content ul, .markdown-content ol { margin: .4rem 0 .65rem 1.25rem; }
.markdown-content ul { list-style: disc; }.markdown-content ol { list-style: decimal; }
.markdown-content code { border-radius: .3rem; background: rgb(15 23 42 / .1); padding: .1rem .3rem; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.markdown-content a { text-decoration: underline; }
.markdown-content pre { margin: .65rem 0; overflow-x: auto; border-radius: .5rem; background: rgb(15 23 42 / .08); padding: .75rem; }
.markdown-content pre code { background: transparent; padding: 0; }
.markdown-content blockquote { margin: .65rem 0; border-left: 3px solid rgb(14 165 233); padding-left: .75rem; color: rgb(71 85 105); }
.markdown-content table { margin: .65rem 0; width: 100%; border-collapse: collapse; font-size: .85em; }
.markdown-content th, .markdown-content td { border: 1px solid rgb(226 232 240); padding: .35rem .5rem; text-align: left; }
</style>
