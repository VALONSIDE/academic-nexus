<script setup lang="ts">
const model = defineModel<string>({ default: '' })
</script>
<template><textarea v-model="model" class="min-h-24 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100 disabled:cursor-not-allowed disabled:opacity-50" /></template>
