<script setup lang="ts">
import Dialog from '@/components/ui/dialog/Dialog.vue'
import { Button } from '@/components/ui/button'
defineProps<{title: string; details: string[]; closeLabel: string}>()
const emit = defineEmits<{close: []}>()
</script>
<template>
  <Dialog :open="true" :title="title" @update:open="value => { if (!value) emit('close') }">
    <ul class="max-h-64 space-y-2 overflow-y-auto rounded-xl bg-rose-50 p-4 text-sm leading-6 text-rose-900"><li v-for="detail in details" :key="detail">{{ detail }}</li></ul>
    <div class="mt-5 flex justify-end"><Button type="button" @click="emit('close')">{{ closeLabel }}</Button></div>
  </Dialog>
</template>
