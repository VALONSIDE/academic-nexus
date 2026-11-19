<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import DashboardLayout from '@/components/DashboardLayout.vue'
import NotificationInbox from '@/components/NotificationInbox.vue'
import { Card } from '@/components/ui/card'
const route = useRoute()
const { t } = useI18n()
const workspace = computed(() => String(route.meta.role))
</script>

<template>
  <DashboardLayout>
    <div class="mx-auto max-w-4xl"><h1 class="text-3xl font-semibold">{{ t('notificationHistory') }}</h1>
      <Card class="mt-6 p-5 sm:p-6"><NotificationInbox mode="history" :workspace="workspace" /></Card>
    </div>
  </DashboardLayout>
</template>
