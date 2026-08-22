<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/utils'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    variant?: 'default' | 'outline' | 'ghost'
    size?: 'default' | 'sm' | 'lg' | 'icon'
  }>(),
  { variant: 'default', size: 'default' },
)

const classes = computed(() =>
  cn(
    'inline-flex shrink-0 items-center justify-center whitespace-nowrap rounded-lg font-medium transition-colors disabled:pointer-events-none disabled:opacity-50',
    props.variant === 'default' && 'bg-slate-900 text-white shadow-sm hover:bg-slate-800',
    props.variant === 'outline' && 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
    props.variant === 'ghost' && 'text-slate-600 hover:bg-slate-100',
    props.size === 'default' && 'h-10 px-4 text-sm',
    props.size === 'sm' && 'h-8 px-3 text-xs',
    props.size === 'lg' && 'h-11 px-5 text-base',
    props.size === 'icon' && 'h-9 w-9',
  ),
)
</script>

<template>
  <button v-bind="$attrs" :class="classes"><slot /></button>
</template>
