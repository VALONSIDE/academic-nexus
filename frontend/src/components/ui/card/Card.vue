<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <section :class="cn('rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/30', props.class)"><slot /></section>
</template>
