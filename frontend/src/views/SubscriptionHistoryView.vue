<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { authApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { SubscriptionHistoryEntry } from '@/lib/workspace'

const { t, locale } = useI18n()
const auth = useAuthStore()
const route = useRoute()
const institution = computed(() => typeof route.query.institution === 'string' ? route.query.institution : '')
const entries = ref<SubscriptionHistoryEntry[]>([])
const page = ref(0)
const more = ref(false)
const loading = ref(false)
const error = ref(false)
let request = 0
async function load() {
  if (!auth.state.token || !institution.value) return
  const current = ++request
  loading.value = true
  error.value = false
  try {
    const result = await authApi.subscriptionHistory(auth.state.token, institution.value, page.value * 30)
    if (current !== request) return
    entries.value = result.items
    more.value = result.more
  } catch {
    if (current === request) error.value = true
  } finally {
    if (current === request) loading.value = false
  }
}
watch(page, load)
watch(institution, () => { if (page.value) page.value = 0; else void load() })
onMounted(load)
</script>

<template>
  <DashboardLayout>
    <div class="mx-auto max-w-5xl">
      <RouterLink :to="{path: '/admin/subscriptions', query: {institution}}" class="text-sm font-medium text-sky-700">{{ t('subscriptionManagement') }}</RouterLink>
      <h1 class="mt-3 text-3xl font-semibold">{{ t('subscriptionHistory') }}</h1>
      <p class="mt-2 text-sm text-slate-500">{{ institution }}</p>
      <Card class="mt-6 p-5">
        <p v-if="error" class="text-rose-700" role="alert">{{ t('updateFailed') }}</p>
        <p v-else-if="loading">{{ t('loading') }}</p>
        <p v-else-if="!entries.length" class="text-sm text-slate-500">{{ t('historyEmpty') }}</p>
        <ul v-else class="divide-y divide-slate-100">
          <li v-for="entry in entries" :key="entry.kind + entry.id" class="flex flex-wrap justify-between gap-2 py-4 text-sm">
            <div><p class="font-medium">{{ t(`event_${entry.kind}`) }} <span v-if="entry.plan">· {{ entry.plan.toUpperCase() }}</span></p><p class="mt-1 text-slate-500">{{ entry.actor || '—' }}</p></div>
            <div class="text-right text-slate-600"><time>{{ new Date(entry.created_at).toLocaleString(locale) }}</time><p v-if="entry.details.available !== undefined">{{ entry.details.previous }} → {{ entry.details.available }}</p><p v-else-if="entry.details.quantity !== undefined">{{ t('inventoryQuantity') }} · {{ entry.details.quantity }}</p></div>
          </li>
        </ul>
        <div v-if="page || more" class="mt-3 flex justify-between"><Button variant="outline" :disabled="!page || loading" @click="page--">{{ t('rankingPrevious') }}</Button><Button variant="outline" :disabled="!more || loading" @click="page++">{{ t('rankingNext') }}</Button></div>
      </Card>
    </div>
  </DashboardLayout>
</template>
