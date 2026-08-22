<script setup lang="ts">
import { AlertCircle, X } from 'lucide-vue-next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

defineProps<{
  title: string
  details: string[]
  closeLabel: string
}>()

const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div class="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-5" role="dialog" aria-modal="true" @click.self="emit('close')">
    <Card class="w-full max-w-xl p-6 shadow-2xl">
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-center gap-3 text-rose-700"><span class="grid h-9 w-9 place-items-center rounded-full bg-rose-100"><AlertCircle class="h-5 w-5" /></span><h2 class="font-semibold">{{ title }}</h2></div>
        <button class="grid h-8 w-8 place-items-center rounded-lg text-slate-600 hover:bg-slate-100" type="button" :aria-label="closeLabel" @click="emit('close')"><X class="h-4 w-4" /></button>
      </div>
      <ul class="mt-5 max-h-64 space-y-2 overflow-y-auto rounded-xl bg-rose-50 p-4 text-sm leading-6 text-rose-900">
        <li v-for="detail in details" :key="detail">{{ detail }}</li>
      </ul>
      <div class="mt-5 flex justify-end"><Button type="button" @click="emit('close')">{{ closeLabel }}</Button></div>
    </Card>
  </div>
</template>
