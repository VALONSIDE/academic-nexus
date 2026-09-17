<script setup lang="ts">
import { computed, onMounted, ref, watch, type Component } from 'vue'
import { CheckCircle2, ChevronDown, Eye, RefreshCw, Search, Sparkles, UserRound, UsersRound, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { ApiError, authApi } from '@/api/client'
import DashboardLayout from '@/components/DashboardLayout.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { MatchedMentor, MatchedStudent, MentorSelection, MentorSelectionSettings, SelectionStatus } from '@/types/auth'

type Candidate = MatchedMentor | MatchedStudent
type SortMode = 'recommended' | 'college' | 'score' | 'name'

const auth = useAuthStore()
const router = useRouter()
const { t } = useI18n()
const isStudent = computed(() => auth.state.user?.roles.includes('student') ?? false)
const mentors = ref<MatchedMentor[]>([])
const students = ref<MatchedStudent[]>([])
const selections = ref<MentorSelection[]>([])
const mentorSettings = ref<MentorSelectionSettings | null>(null)
const loading = ref(false)
const actingId = ref('')
const error = ref('')
const notice = ref('')
const search = ref('')
const college = ref('all')
const sort = ref<SortMode>('recommended')
const detail = ref<Candidate | null>(null)
const page = ref(1)
const pageSize = 20

const items = computed<Candidate[]>(() => isStudent.value ? mentors.value : students.value)
const title = computed(() => t(isStudent.value ? 'matchedMentors' : 'matchedStudents'))
const colleges = computed(() => [...new Set(items.value.map((item) => item.department).filter((item): item is string => Boolean(item)))].sort((left, right) => left.localeCompare(right)))
const filteredItems = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  const matches = items.value.filter((item) => {
    const tags = isMentor(item) ? [...item.research_directions, ...item.representative_papers] : [...item.research_interests, ...item.skills]
    const haystack = [item.full_name, item.username, item.university, item.department, ...tags].filter(Boolean).join(' ').toLocaleLowerCase()
    return (!query || haystack.includes(query)) && (college.value === 'all' || item.department === college.value)
  })
  if (sort.value === 'recommended') return matches
  return [...matches].sort((left, right) => {
    if (sort.value === 'name') return left.full_name.localeCompare(right.full_name)
    if (sort.value === 'score') return right.match_score - left.match_score || left.full_name.localeCompare(right.full_name)
    return Number(right.same_college) - Number(left.same_college) || right.match_score - left.match_score || left.full_name.localeCompare(right.full_name)
  })
})

const pageCount = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / pageSize)))
const visibleItems = computed(() => filteredItems.value.slice((page.value - 1) * pageSize, page.value * pageSize))
watch([search, college, sort, items], () => { page.value = 1 })

function isMentor(item: Candidate): item is MatchedMentor { return 'research_directions' in item }
function candidateIcon(item: Candidate): Component { return isMentor(item) ? UserRound : UsersRound }
function tags(item: Candidate) { return isMentor(item) ? item.research_directions : item.research_interests }
function selectionFor(userId: string) { return selections.value.find((item) => isStudent.value ? item.mentor_user_id === userId : item.student_user_id === userId) }
function labelFor(status?: SelectionStatus) { const labels: Record<SelectionStatus, string> = { pending_student: 'selectedPending', pending_mentor: isStudent.value ? 'mentorInvitedYou' : 'invitationSent', confirmed: 'selectionConfirmed', rejected: 'rejected', cancelled: 'cancelled' }; return status ? t(labels[status]) : '' }
function statusClass(status?: SelectionStatus) { return status === 'confirmed' ? 'bg-emerald-100 text-emerald-800' : status?.startsWith('pending') ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600' }
function errorText(exception: unknown) { if (exception instanceof ApiError) { if (exception.code === 'selection_closed') return t('selectionClosed'); if (exception.code === 'mentor_capacity_full') return t('mentorCapacityFull'); if (exception.code === 'student_choice_limit_reached') return t('selectionOperationFailed'); if (exception.code === 'portrait_required') return t('matchingPortraitRequired') }; return t('selectionOperationFailed') }
function clearFilters() { search.value = ''; college.value = 'all'; sort.value = 'recommended' }
function openAdvisor(item: Candidate) { router.push({ path: `/${isStudent.value ? 'student' : 'mentor'}/assistant`, query: { topic: 'selection_advisor', candidate: item.full_name } }) }

async function load() {
  if (!auth.state.token) return
  loading.value = true; error.value = ''
  try {
    if (isStudent.value) {
      const [matches, current] = await Promise.all([authApi.mentorRecommendations(auth.state.token), authApi.studentSelections(auth.state.token)])
      mentors.value = matches.items; selections.value = current
    } else {
      const [matches, current, settings] = await Promise.all([authApi.studentCandidates(auth.state.token), authApi.mentorSelectionCandidates(auth.state.token), authApi.mentorSelectionSettings(auth.state.token)])
      students.value = matches.items; selections.value = current.items.map((item) => item.selection); mentorSettings.value = settings
    }
  } catch (exception) { error.value = errorText(exception) } finally { loading.value = false }
}
async function act(id: string, action: () => Promise<unknown>) { actingId.value = id; error.value = ''; notice.value = ''; try { await action(); notice.value = t('selectionUpdated'); await load() } catch (exception) { error.value = errorText(exception) } finally { actingId.value = '' } }
function studentAction(item: MatchedMentor) { if (!auth.state.token) return; const selection = selectionFor(item.user_id); if (selection?.status === 'pending_student') return act(selection.id, () => authApi.cancelMentorChoice(auth.state.token!, selection.id)); if (selection?.status !== 'confirmed') return act(item.user_id, () => authApi.chooseMentor(auth.state.token!, item.user_id)) }
function mentorAction(item: MatchedStudent) { if (!auth.state.token) return; const selection = selectionFor(item.user_id); if (selection?.status === 'pending_student') return act(selection.id, () => authApi.confirmSelection(auth.state.token!, selection.id)); if (!selection || ['rejected', 'cancelled'].includes(selection.status)) return act(item.user_id, () => authApi.inviteStudent(auth.state.token!, item.user_id)) }
function mentorReject(item: MatchedStudent) { const selection = selectionFor(item.user_id); if (auth.state.token && selection) return act(selection.id, () => authApi.rejectSelection(auth.state.token!, selection.id)) }

onMounted(load)
</script>

<template>
  <DashboardLayout>
    <div class="mx-auto w-full max-w-7xl">
      <div class="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div><p class="text-sm font-medium text-sky-700">{{ t('mutualSelection') }}</p><h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900">{{ title }}</h1><p class="mt-3 max-w-3xl leading-7 text-slate-600">{{ t(isStudent ? 'selectionIntro' : 'mentorMatchingDescriptionForMentor') }}</p></div>
        <Button variant="outline" :disabled="loading" @click="load"><RefreshCw class="mr-2 h-4 w-4" :class="loading ? 'animate-spin' : ''" />{{ t('refreshMatches') }}</Button>
      </div>
      <Card v-if="mentorSettings" class="mt-7 grid gap-4 border-sky-100 bg-sky-50/60 p-5 shadow-none sm:grid-cols-3"><div><p class="text-xs text-slate-500">{{ t('selectionCapacity') }}</p><p class="mt-1 text-2xl font-semibold">{{ mentorSettings.confirmed_count }}/{{ mentorSettings.capacity }}</p></div><div><p class="text-xs text-slate-500">{{ t('availableSlots') }}</p><p class="mt-1 text-2xl font-semibold text-sky-700">{{ mentorSettings.available_slots }}</p></div><div><p class="text-xs text-slate-500">{{ t('selectionMode') }}</p><p class="mt-1 font-medium">{{ t(mentorSettings.selection_mode === 'first_come' ? 'firstComeSelection' : 'manualSelection') }}</p></div></Card>
      <p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ notice }}</p><p v-if="error" class="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{{ error }}</p>
      <Card class="mt-7 p-4 shadow-sm"><div class="grid gap-3 lg:grid-cols-[minmax(0,1fr)_12rem_12rem_auto]"><label class="relative"><Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input v-model="search" class="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100" :placeholder="t('searchUsersPlaceholder')" /></label><label class="relative"><select v-model="college" class="h-10 w-full appearance-none rounded-lg border border-slate-200 bg-white px-3 pr-8 text-sm outline-none focus:border-sky-500"><option value="all">{{ t('allColleges') }}</option><option v-for="item in colleges" :key="item" :value="item">{{ item }}</option></select><ChevronDown class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /></label><label class="relative"><select v-model="sort" class="h-10 w-full appearance-none rounded-lg border border-slate-200 bg-white px-3 pr-8 text-sm outline-none focus:border-sky-500"><option value="recommended">{{ t('recommendedOrder') }}</option><option value="college">{{ t('sameCollegeFirst') }}</option><option value="score">{{ t('sortByFit') }}</option><option value="name">{{ t('sortByName') }}</option></select><ChevronDown class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /></label><Button variant="ghost" class="justify-center" @click="clearFilters">{{ t('clearFilters') }}</Button></div><p class="mt-3 text-xs text-slate-500">{{ t('showingCandidates', { shown: filteredItems.length, total: items.length }) }}</p></Card>
      <div v-if="loading" class="grid min-h-64 place-items-center text-sm text-slate-500">{{ t('loading') }}</div>
      <div v-else-if="filteredItems.length" class="mt-7 grid gap-5 xl:grid-cols-2"><Card v-for="item in visibleItems" :key="item.user_id" class="overflow-hidden p-0 shadow-sm"><div class="flex items-start justify-between gap-4 border-b border-slate-100 p-5"><div class="flex min-w-0 items-start gap-3"><span class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-900 text-white"><component :is="candidateIcon(item)" class="h-5 w-5" /></span><div class="min-w-0"><div class="flex flex-wrap items-center gap-2"><h2 class="truncate font-semibold text-slate-900">{{ item.full_name }}</h2><span v-if="item.same_college" class="rounded-full bg-sky-100 px-2 py-0.5 text-[11px] font-medium text-sky-800">{{ t('sameCollegeFirst') }}</span></div><p class="mt-1 truncate text-sm text-slate-500">{{ item.username }}</p></div></div><div class="shrink-0 rounded-xl bg-sky-50 px-3 py-2 text-right"><p class="text-xs text-sky-800">{{ t('matchScore') }}</p><p class="mt-0.5 text-xl font-semibold text-sky-700">{{ item.match_score }}/100</p></div></div><div class="p-5"><div class="grid gap-2 text-xs sm:grid-cols-2"><p class="rounded-lg bg-slate-50 px-3 py-2 text-slate-600"><span class="font-medium text-slate-800">{{ t('institution') }}：</span>{{ item.university || '—' }}</p><p class="rounded-lg bg-slate-50 px-3 py-2 text-slate-600"><span class="font-medium text-slate-800">{{ t('college') }}：</span>{{ item.department || '—' }}</p></div><div class="mt-4 flex flex-wrap gap-2"><span v-for="tag in tags(item)" :key="tag" class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{{ tag }}</span></div><div v-if="selectionFor(item.user_id)" class="mt-5 flex items-center gap-2"><CheckCircle2 class="h-4 w-4" /><span class="rounded-full px-2.5 py-1 text-xs font-medium" :class="statusClass(selectionFor(item.user_id)?.status)">{{ labelFor(selectionFor(item.user_id)?.status) }}</span></div><div class="mt-5 flex flex-wrap gap-2"><Button variant="outline" @click="detail = item"><Eye class="mr-1.5 h-4 w-4" />{{ t('viewDetails') }}</Button><Button variant="outline" @click="openAdvisor(item)"><Sparkles class="mr-1.5 h-4 w-4" />{{ t('askAiAboutCandidate') }}</Button><Button v-if="isStudent && isMentor(item)" :variant="selectionFor(item.user_id)?.status === 'pending_student' || selectionFor(item.user_id)?.status === 'pending_mentor' ? 'outline' : 'default'" :disabled="Boolean(actingId) || selectionFor(item.user_id)?.status === 'confirmed'" @click="selectionFor(item.user_id)?.status === 'pending_mentor' ? act(selectionFor(item.user_id)!.id, () => authApi.cancelMentorChoice(auth.state.token!, selectionFor(item.user_id)!.id)) : studentAction(item)">{{ selectionFor(item.user_id)?.status === 'pending_student' || selectionFor(item.user_id)?.status === 'pending_mentor' ? t('cancelChoice') : selectionFor(item.user_id)?.status === 'confirmed' ? t('selectionConfirmed') : t('selectMentor') }}</Button><Button v-if="!isStudent && !isMentor(item)" :disabled="Boolean(actingId) || ['confirmed', 'pending_mentor'].includes(selectionFor(item.user_id)?.status || '')" @click="mentorAction(item)">{{ selectionFor(item.user_id)?.status === 'pending_student' ? t('confirmStudent') : selectionFor(item.user_id)?.status === 'confirmed' ? t('selectionConfirmed') : selectionFor(item.user_id)?.status === 'pending_mentor' ? t('invitationSent') : t('inviteStudent') }}</Button><Button v-if="!isStudent && !isMentor(item) && ['pending_student', 'pending_mentor'].includes(selectionFor(item.user_id)?.status || '')" variant="outline" :disabled="Boolean(actingId)" @click="mentorReject(item)">{{ selectionFor(item.user_id)?.status === 'pending_mentor' ? t('withdrawInvitation') : t('rejectStudent') }}</Button></div></div></Card></div>
      <Card v-else-if="!loading" class="mt-7 grid min-h-56 place-items-center border-dashed bg-slate-50 p-8 text-center shadow-none"><p class="max-w-lg text-sm leading-7 text-slate-600">{{ items.length ? t('selectionActivityEmpty') : t('noMatches') }}</p></Card>
      <nav v-if="!loading && pageCount > 1" class="mt-6 flex items-center justify-center gap-4" :aria-label="t('rankingPages')"><Button variant="outline" :disabled="page === 1" @click="page--">{{ t('rankingPrevious') }}</Button><span class="text-sm text-slate-600">{{ page }} / {{ pageCount }}</span><Button variant="outline" :disabled="page === pageCount" @click="page++">{{ t('rankingNext') }}</Button></nav>
    </div>
    <div v-if="detail" class="fixed inset-0 z-50 grid place-items-center bg-slate-950/35 p-4" @click.self="detail = null"><Card class="max-h-[90vh] w-full max-w-3xl overflow-y-auto p-6"><div class="flex items-start justify-between gap-4"><div><p class="text-sm font-medium text-sky-700">{{ t('candidateDetails') }}</p><h2 class="mt-1 text-2xl font-semibold text-slate-900">{{ detail.full_name }}</h2><p class="mt-2 text-sm text-slate-500">{{ detail.university }} · {{ detail.department }}</p></div><Button size="icon" variant="ghost" @click="detail = null"><X class="h-4 w-4" /></Button></div><template v-if="isMentor(detail)"><section class="mt-6"><h3 class="font-semibold">{{ t('researchDirections') }}</h3><div class="mt-3 flex flex-wrap gap-2"><span v-for="tag in detail.research_directions" :key="tag" class="rounded-full bg-sky-50 px-3 py-1 text-sm text-sky-800">{{ tag }}</span></div></section><section class="mt-6"><h3 class="font-semibold">{{ t('candidatePapers') }}</h3><ul class="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700"><li v-for="paper in detail.representative_papers" :key="paper">{{ paper }}</li></ul></section><section class="mt-6"><h3 class="font-semibold">{{ t('candidateProjects') }}</h3><p class="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">{{ detail.research_projects || '—' }}</p></section><section class="mt-6"><h3 class="font-semibold">{{ t('mentoringStyle') }}</h3><p class="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">{{ detail.mentoring_style || '—' }}</p></section></template><template v-else><section class="mt-6"><h3 class="font-semibold">{{ t('researchInterests') }}</h3><div class="mt-3 flex flex-wrap gap-2"><span v-for="tag in detail.research_interests" :key="tag" class="rounded-full bg-sky-50 px-3 py-1 text-sm text-sky-800">{{ tag }}</span></div></section><section class="mt-6"><h3 class="font-semibold">{{ t('skills') }}</h3><div class="mt-3 flex flex-wrap gap-2"><span v-for="tag in detail.skills" :key="tag" class="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">{{ tag }}</span></div></section><section class="mt-6"><h3 class="font-semibold">{{ t('academicAbility') }}</h3><p class="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">{{ detail.academic_performance || '—' }}</p></section><section class="mt-6"><h3 class="font-semibold">{{ t('academicGoals') }}</h3><p class="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">{{ detail.academic_goals || '—' }}</p></section><section class="mt-6"><h3 class="font-semibold">{{ t('researchExperience') }}</h3><p class="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">{{ detail.research_experience || '—' }}</p></section></template><div class="mt-8 flex justify-end"><Button @click="openAdvisor(detail)">{{ t('askAiAboutCandidate') }}</Button></div></Card></div>
  </DashboardLayout>
</template>
