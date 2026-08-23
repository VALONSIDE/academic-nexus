<script setup lang="ts">
import { Check, ChevronDown } from 'lucide-vue-next'
import {
  SelectContent,
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  SelectPortal,
  SelectRoot,
  SelectTrigger,
  SelectValue,
  SelectViewport,
} from 'reka-ui'

import { cn } from '@/lib/utils'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

const model = defineModel<string>({ default: '' })
const props = withDefaults(defineProps<{
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  class?: string
}>(), {
  placeholder: 'Select an option',
})
</script>

<template>
  <SelectRoot v-model="model" :disabled="props.disabled">
    <SelectTrigger :class="cn('flex h-10 w-full items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 text-left text-sm text-slate-900 shadow-sm outline-none transition focus:border-sky-500 focus:ring-3 focus:ring-sky-100 data-[placeholder]:text-slate-400 disabled:cursor-not-allowed disabled:opacity-50', props.class)">
      <SelectValue :placeholder="props.placeholder" class="min-w-0 truncate" />
      <ChevronDown class="h-4 w-4 shrink-0 text-slate-400" />
    </SelectTrigger>
    <SelectPortal>
      <SelectContent position="popper" :side-offset="6" class="z-50 max-h-72 min-w-[var(--reka-select-trigger-width)] overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-xl shadow-slate-900/10">
        <SelectViewport class="max-h-72 overflow-y-auto">
          <SelectItem
            v-for="option in props.options"
            :key="option.value"
            :value="option.value"
            :disabled="option.disabled"
            class="relative flex min-h-9 cursor-default select-none items-center rounded-lg py-2 pl-8 pr-3 text-sm text-slate-700 outline-none data-[highlighted]:bg-slate-100 data-[state=checked]:font-medium data-[disabled]:pointer-events-none data-[disabled]:opacity-45"
          >
            <SelectItemIndicator class="absolute left-2.5 inline-flex items-center justify-center text-sky-700"><Check class="h-4 w-4" /></SelectItemIndicator>
            <SelectItemText class="truncate">{{ option.label }}</SelectItemText>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
