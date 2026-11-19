<script setup lang="ts">
import { ToggleGroupRoot, ToggleGroupItem } from 'reka-ui'
const model = defineModel<string>({ default: '' })
defineProps<{ options: { value: string; label: string; disabled?: boolean }[]; disabled?: boolean; label: string }>()
</script>
<template>
  <ToggleGroupRoot type="single" :model-value="model" :disabled="disabled" :aria-label="label" class="inline-flex h-10 max-w-full items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1" @update:model-value="value => { if (value) model = String(value) }">
    <ToggleGroupItem v-for="option in options" :key="option.value" :value="option.value" :disabled="option.disabled" class="inline-flex h-8 items-center justify-center whitespace-nowrap rounded-md px-3 text-xs font-medium text-slate-600 outline-none transition focus-visible:ring-2 focus-visible:ring-sky-500 data-[state=on]:bg-slate-900 data-[state=on]:text-white disabled:opacity-50">{{ option.label }}</ToggleGroupItem>
  </ToggleGroupRoot>
</template>
