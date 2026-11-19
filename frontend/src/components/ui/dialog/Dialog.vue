<script setup lang="ts">
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription, DialogClose } from 'reka-ui'
import { X } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
const open = defineModel<boolean>('open', { default: false })
defineProps<{ title: string; description?: string }>()
</script>
<template>
  <DialogRoot v-model:open="open">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-slate-950/40 data-[state=open]:animate-in" />
      <DialogContent class="fixed left-1/2 top-1/2 z-50 max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-xl focus:outline-none">
        <div class="mb-5 flex items-start justify-between gap-4">
          <div><DialogTitle class="text-xl font-semibold text-slate-900">{{ title }}</DialogTitle><DialogDescription :class="description ? 'mt-2 text-sm text-slate-500' : 'sr-only'">{{ description || title }}</DialogDescription></div>
          <DialogClose as-child><Button size="icon" variant="ghost" aria-label="关闭 / Close"><X class="h-4 w-4" /></Button></DialogClose>
        </div>
        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
