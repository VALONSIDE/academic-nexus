<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { authApi } from '@/api/client'
import ResourceCards from '@/components/ResourceCards.vue'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { LearningResource } from '@/types/auth'

const auth = useAuthStore()
const { t } = useI18n()
const resources = ref<LearningResource[]>([])
const error = ref('')

onMounted(async () => {
  if (!auth.state.token) return
  try {
    resources.value = (await authApi.recommendedResources(auth.state.token, 3)).items
  } catch {
    resources.value = []
  }
})
</script>

<template>
  <section class="mt-7"><div class="mb-4 flex items-center justify-between"><div><h2 class="text-lg font-semibold text-slate-900">{{ t('recommendedForYou') }}</h2><p class="mt-1 text-sm text-slate-500">{{ t('learningResources') }}</p></div><RouterLink to="/student/resources" class="text-sm font-medium text-sky-700 hover:text-sky-800">{{ t('allResources') }}</RouterLink></div><ResourceCards v-if="resources.length" compact :resources="resources" @error="error = $event" /><Card v-else class="border-dashed bg-slate-50 p-5 text-sm leading-6 text-slate-600 shadow-none">{{ t('recommendedResourcesEmpty') }}</Card><p v-if="error" class="mt-3 text-sm text-rose-700">{{ error }}</p></section>
</template>
