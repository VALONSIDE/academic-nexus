<script setup lang="ts">
import { cn } from '@/lib/utils'

defineOptions({ inheritAttrs: false })
const model = defineModel<string>()
const props = defineProps<{ class?: string }>()
</script>

<template>
  <input
    v-bind="$attrs"
    v-model="model"
    :class="cn('flex h-10 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-3 focus:ring-sky-100 disabled:cursor-not-allowed disabled:opacity-50', props.class)"
  />
</template>
