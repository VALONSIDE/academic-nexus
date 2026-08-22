<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { Button } from '@/components/ui/button'
import type { MentorAcademicProfile, StudentAcademicProfile } from '@/types/auth'

const props = defineProps<{
  role: 'student' | 'mentor'
  initialValue?: StudentAcademicProfile | MentorAcademicProfile | null
  submitting?: boolean
  submitLabel: string
}>()

const emit = defineEmits<{
  submit: [payload: StudentAcademicProfile | MentorAcademicProfile]
}>()

const { t } = useI18n()
const isStudent = computed(() => props.role === 'student')
const firstTags = ref('')
const secondTags = ref('')
const firstText = ref('')
const secondText = ref('')
const thirdText = ref('')

function tagsToText(value: unknown): string {
  return Array.isArray(value) ? value.join('\n') : ''
}

function hydrate(value: StudentAcademicProfile | MentorAcademicProfile | null | undefined) {
  if (props.role === 'student') {
    const profile = value as StudentAcademicProfile | null | undefined
    firstTags.value = tagsToText(profile?.research_interests)
    secondTags.value = tagsToText(profile?.skills)
    firstText.value = profile?.academic_performance || ''
    secondText.value = profile?.academic_goals || ''
    thirdText.value = profile?.research_experience || ''
  } else {
    const profile = value as MentorAcademicProfile | null | undefined
    firstTags.value = tagsToText(profile?.research_directions)
    secondTags.value = tagsToText(profile?.representative_papers)
    firstText.value = profile?.research_projects || ''
    secondText.value = profile?.mentoring_style || ''
    thirdText.value = ''
  }
}

watch(() => props.initialValue, hydrate, { immediate: true })

function parseTags(value: string): string[] {
  return value.split(/[，,\n]/).map(item => item.trim()).filter(Boolean)
}

function submit() {
  if (props.role === 'student') {
    emit('submit', {
      research_interests: parseTags(firstTags.value),
      skills: parseTags(secondTags.value),
      academic_performance: firstText.value,
      academic_goals: secondText.value,
      research_experience: thirdText.value,
    })
    return
  }
  emit('submit', {
    research_directions: parseTags(firstTags.value),
    representative_papers: parseTags(secondTags.value),
    research_projects: firstText.value,
    mentoring_style: secondText.value,
  })
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="submit">
    <label class="grid gap-1.5 text-sm font-medium text-slate-700">
      {{ isStudent ? t('researchInterests') : t('researchDirections') }}
      <textarea v-model="firstTags" class="min-h-24 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-sky-600 focus:ring-2 focus:ring-sky-100" required :placeholder="isStudent ? t('studentInterestPlaceholder') : t('directionPlaceholder')" />
      <span class="font-normal text-slate-400">{{ t('tagHint') }}</span>
    </label>

    <label class="grid gap-1.5 text-sm font-medium text-slate-700">
      {{ isStudent ? t('skills') : t('representativePapers') }}
      <textarea v-model="secondTags" class="min-h-24 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-sky-600 focus:ring-2 focus:ring-sky-100" required :placeholder="isStudent ? t('studentSkillsPlaceholder') : t('papersPlaceholder')" />
      <span class="font-normal text-slate-400">{{ t('tagHint') }}</span>
    </label>

    <label class="grid gap-1.5 text-sm font-medium text-slate-700">
      {{ isStudent ? t('academicPerformance') : t('researchProjects') }}
      <textarea v-model="firstText" class="min-h-28 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-sky-600 focus:ring-2 focus:ring-sky-100" required :placeholder="isStudent ? t('performancePlaceholder') : t('projectsPlaceholder')" />
    </label>

    <label class="grid gap-1.5 text-sm font-medium text-slate-700">
      {{ isStudent ? t('academicGoals') : t('mentoringStyle') }}
      <textarea v-model="secondText" class="min-h-28 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-sky-600 focus:ring-2 focus:ring-sky-100" required :placeholder="isStudent ? t('goalsPlaceholder') : t('stylePlaceholder')" />
    </label>

    <label v-if="isStudent" class="grid gap-1.5 text-sm font-medium text-slate-700">
      {{ t('researchExperience') }}
      <textarea v-model="thirdText" class="min-h-32 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-sky-600 focus:ring-2 focus:ring-sky-100" required :placeholder="t('experiencePlaceholder')" />
    </label>

    <Button class="w-full" type="submit" size="lg" :disabled="submitting">
      {{ submitting ? t('loading') : submitLabel }}
    </Button>
  </form>
</template>
