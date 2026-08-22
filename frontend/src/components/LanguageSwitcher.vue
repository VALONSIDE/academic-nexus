<script setup lang="ts">
import { Globe2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { toggleLocale } from '@/i18n'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

async function changeLocale() {
  const nextLocale = toggleLocale()
  if (auth.state.token && auth.state.user) await auth.setLocale(nextLocale)
}
</script>

<template>
  <Button variant="ghost" size="sm" type="button" :aria-label="t('language')" @click="changeLocale">
    <Globe2 class="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
    {{ t('language') }}
  </Button>
</template>
