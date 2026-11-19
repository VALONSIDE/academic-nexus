<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Bell, ChevronRight } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import Dialog from '@/components/ui/dialog/Dialog.vue'
import ToggleGroup from '@/components/ui/toggle-group/ToggleGroup.vue'
import { useAuthStore } from '@/stores/auth'
import { notificationDestination, type WorkspaceNotification } from '@/lib/workspace'

const props = defineProps<{ mode: 'bell' | 'latest' | 'history'; workspace: string }>()
const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const inboxOpen = ref(false)
const detailOpen = ref(false)
const detail = ref<WorkspaceNotification | null>(null)
const items = ref<WorkspaceNotification[]>([])
const unread = ref(0)
const total = ref(0)
const page = ref(0)
const filter = ref('all')
const loading = ref(false)
const error = ref(false)
const limit = computed(() => props.mode === 'latest' ? 5 : 15)
const historyPath = computed(() => `/${props.workspace}/notifications`)
let pending = 0

async function load() {
  if (!auth.state.token) return
  const request = ++pending
  loading.value = true
  error.value = false
  try {
    const result = await authApi.notifications(auth.state.token, filter.value === 'unread', limit.value, page.value * limit.value)
    if (request !== pending) return
    items.value = result.items
    unread.value = result.unread
    total.value = result.total
    if (page.value && page.value * limit.value >= result.total) page.value = Math.max(0, Math.ceil(result.total / limit.value) - 1)
  } catch {
    if (request === pending) error.value = true
  } finally {
    if (request === pending) loading.value = false
  }
}

function date(value: string) {
  return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

async function openItem(item: WorkspaceNotification) {
  detail.value = item
  detailOpen.value = true
  if (!item.read_at && auth.state.token) {
    try {
      await authApi.readNotification(auth.state.token, item.id)
      await load()
      window.dispatchEvent(new Event('workspace-notifications-changed'))
    } catch { error.value = true }
  }
}

async function markAll() {
  if (!auth.state.token) return
  try {
    await authApi.readAllNotifications(auth.state.token)
    page.value = 0
    await load()
    window.dispatchEvent(new Event('workspace-notifications-changed'))
  } catch { error.value = true }
}

function follow() {
  if (!detail.value) return
  const destination = notificationDestination(detail.value)
  detailOpen.value = false
  inboxOpen.value = false
  void router.push(destination)
}

watch(filter, () => {
  if (page.value) page.value = 0
  else void load()
})
watch(page, load)
watch(inboxOpen, value => { if (value) void load() })
let refreshTimer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  void load()
  window.addEventListener('workspace-notifications-changed', load)
  if (props.mode === 'bell') refreshTimer = setInterval(load, 30000)
})
onUnmounted(() => {
  pending++
  clearInterval(refreshTimer)
  window.removeEventListener('workspace-notifications-changed', load)
})
</script>

<template>
  <Button v-if="mode === 'bell'" size="icon" variant="ghost" class="relative" :aria-label="t('notificationCenter') + ' ' + unread" @click="inboxOpen = true">
    <Bell class="size-5" /><span v-if="unread" class="absolute right-1.5 top-1.5 size-2 rounded-full bg-rose-600 ring-2 ring-white" />
  </Button>
  <component :is="mode === 'bell' ? Dialog : 'section'" v-bind="mode === 'bell' ? {open: inboxOpen, title: t('notificationCenter'), 'onUpdate:open': (value: boolean) => { inboxOpen = value }} : {}">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h2 v-if="mode === 'latest'" class="font-semibold">{{ t('latestNotifications') }}</h2>
      <ToggleGroup v-else v-model="filter" :label="t('notificationCenter')" :options="[{value: 'all', label: t('all')}, {value: 'unread', label: t('unreadNotifications')}]" />
      <Button v-if="unread && mode !== 'latest'" size="sm" variant="ghost" @click="markAll">{{ t('markAllRead') }}</Button>
      <RouterLink v-if="mode !== 'history'" :to="historyPath" class="text-sm font-medium text-sky-700" @click="inboxOpen = false">{{ t('notificationHistory') }}</RouterLink>
    </div>
    <p v-if="error" class="py-4 text-sm text-rose-700" role="alert">{{ t('updateFailed') }} <Button size="sm" variant="outline" @click="load">{{ t('refreshMatches') }}</Button></p>
    <p v-else-if="loading && !items.length" class="py-5 text-sm text-slate-500">{{ t('loading') }}</p>
    <p v-else-if="!items.length" class="rounded-xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">{{ t('notificationsEmpty') }}</p>
    <ul v-else class="divide-y divide-slate-100">
      <li v-for="item in items" :key="item.id">
        <Button variant="ghost" class="h-auto w-full justify-start gap-3 whitespace-normal px-2 py-3 text-left" @click="openItem(item)">
          <span class="size-2 shrink-0 rounded-full" :class="item.read_at ? 'bg-slate-200' : 'bg-rose-600'" />
          <span class="min-w-0 flex-1"><span class="block font-medium text-slate-900">{{ t(`event_${item.kind}`) }} <template v-if="item.counterpart"> · {{ item.counterpart }}</template></span><span class="mt-1 block text-xs text-slate-500">{{ date(item.created_at) }} <template v-if="item.institution"> · {{ item.institution }}</template></span></span>
          <ChevronRight class="size-4 shrink-0" />
        </Button>
      </li>
    </ul>
    <div v-if="mode === 'history' && (page || total > limit)" class="mt-4 flex justify-between">
      <Button variant="outline" :disabled="page === 0 || loading" @click="page--">{{ t('rankingPrevious') }}</Button>
      <Button variant="outline" :disabled="(page + 1) * limit >= total || loading" @click="page++">{{ t('rankingNext') }}</Button>
    </div>
  </component>
  <Dialog v-model:open="detailOpen" :title="detail ? t(`event_${detail.kind}`) : t('notificationCenter')">
    <template v-if="detail">
      <p class="text-sm text-slate-500">{{ date(detail.created_at) }} <template v-if="detail.actor"> · {{ detail.actor }}</template> <template v-if="detail.institution"> · {{ detail.institution }}</template></p>
      <dl class="mt-4 grid gap-2 text-sm"><div v-if="detail.counterpart">{{ detail.counterpart }}</div>
        <div v-if="detail.details.plan">{{ t('subscriptionTier') }} · {{ detail.details.plan.toUpperCase() }}</div>
        <div v-if="detail.details.quantity !== undefined">{{ t('inventoryQuantity') }} · {{ detail.details.quantity }}</div>
        <div v-if="detail.details.available !== undefined">{{ t('inventoryAvailable') }} · {{ detail.details.available }}</div>
        <div v-if="detail.details.limit !== undefined">{{ t('effectiveSelectionLimit') }} · {{ detail.details.exempt ? t('unlimitedQuota') : detail.details.limit }}</div>
        <div v-if="detail.details.quota_mb !== undefined">{{ t('resourceQuota') }} · {{ detail.details.quota_mb }} MB</div>
      </dl>
      <div class="mt-6 flex justify-end gap-2"><Button variant="outline" @click="detailOpen = false">{{ t('close') }}</Button><Button @click="follow">{{ t('openNotificationDestination') }}</Button></div>
    </template>
  </Dialog>
</template>
