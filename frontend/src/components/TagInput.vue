<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { TagsInputInput, TagsInputItem, TagsInputItemDelete, TagsInputItemText, TagsInputRoot } from 'reka-ui'

const model = defineModel<string[]>({ default: () => [] })
const props = withDefaults(defineProps<{
  placeholder?: string
  disabled?: boolean
  max?: number
}>(), {
  placeholder: '',
  max: 20,
})

const delimiter = /[,，;；、\n\r]+/

function normalize(value: string) {
  return value.trim().replace(/\s+/g, ' ').slice(0, 120)
}

function remove(value: string) {
  model.value = model.value.filter(item => item !== value)
}
</script>

<template>
  <TagsInputRoot
    v-model="model"
    :delimiter="delimiter"
    :convert-value="normalize"
    :max="props.max"
    :disabled="props.disabled"
    add-on-blur
    add-on-paste
    add-on-tab
    class="flex min-h-10 w-full flex-wrap items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm shadow-sm outline-none transition focus-within:border-sky-500 focus-within:ring-3 focus-within:ring-sky-100 data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50"
  >
    <TagsInputItem
      v-for="item in model"
      :key="item"
      :value="item"
      class="inline-flex max-w-full items-center gap-1 rounded-md bg-sky-50 px-2 py-1 text-xs font-medium text-sky-800 outline-none data-[state=active]:ring-2 data-[state=active]:ring-sky-300"
    >
      <TagsInputItemText class="truncate" />
      <TagsInputItemDelete
        class="grid h-4 w-4 shrink-0 place-items-center rounded text-sky-700 transition hover:bg-sky-200 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-sky-400"
        :aria-label="`Remove ${item}`"
        @click.prevent="remove(item)"
      >
        <X class="h-3 w-3" />
      </TagsInputItemDelete>
    </TagsInputItem>
    <TagsInputInput
      :placeholder="props.placeholder"
      class="h-7 min-w-28 flex-1 bg-transparent px-1 text-sm text-slate-900 outline-none placeholder:text-slate-400"
    />
  </TagsInputRoot>
</template>
