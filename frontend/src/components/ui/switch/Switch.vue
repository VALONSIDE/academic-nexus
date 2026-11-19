<script setup lang="ts">
import { SwitchRoot, SwitchThumb } from 'reka-ui'
const model = defineModel<boolean>({ default: false })
defineProps<{ label: string; disabled?: boolean }>()
</script>
<template>
  <label class="flex cursor-pointer items-center justify-between gap-4 text-sm text-slate-700">
    <span>{{ label }}</span>
    <SwitchRoot v-model="model" :disabled="disabled" :aria-label="label" class="inline-flex h-6 w-11 shrink-0 items-center rounded-full bg-slate-200 p-0.5 outline-none transition focus-visible:ring-2 focus-visible:ring-sky-500 data-[state=checked]:bg-slate-900 disabled:opacity-50"><SwitchThumb class="block h-5 w-5 rounded-full bg-white shadow-sm transition-transform data-[state=checked]:translate-x-5" /></SwitchRoot>
  </label>
</template>
