import type {
  AcademicProfileResponse,
  AdminResourceQuotaListResponse,
  AdminAiQuotaListResponse,
  ActivationPayload,
  ActivationStartResponse,
  AdminUserUpdatePayload,
  AuthResponse,
  AiChatResponse,
  AiConversation,
  AiConversationDetail,
  AiQuota,
  AiTopic,
  DashboardOverview,
  LoginPayload,
  ManagedUser,
  ManagedUserListResponse,
  MentorAcademicProfile,
  MentorResourceQuota,
  MentorRecommendationListResponse,
  LearningResource,
  StudentAcademicProfile,
  StudentCandidateListResponse,
  LearningResourceListResponse,
  ResourceType,
  MentorSelection,
  MentorSelectionSettings,
  SelectionCandidateListResponse,
  SelectionSettings,
  AdminSelectionUser,
  AdminSelectionRecordListResponse,
  PreRegistrationAccountListResponse,
  User,
} from '@/types/auth'

const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export class ApiError extends Error {
  constructor(message: string, public readonly details: string[] = [], public readonly code?: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function responseError(response: Response): Promise<ApiError> {
  const body = (await response.json().catch(() => ({}))) as { detail?: string | string[] | { code?: string } }
  const detail = body.detail
  if (Array.isArray(detail)) return new ApiError(detail.join('\n'), detail)
  if (detail && typeof detail === 'object') return new ApiError(detail.code || `Request failed (${response.status})`, [], detail.code)
  return new ApiError(detail || `Request failed (${response.status})`)
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  })
  if (!response.ok) {
    throw await responseError(response)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const authApi = {
  login(payload: LoginPayload) {
    return request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify(payload) })
  },
  activate(payload: ActivationPayload) {
    return request<ActivationStartResponse>('/auth/activate', { method: 'POST', body: JSON.stringify(payload) })
  },
  me(token: string) {
    return request<User>('/auth/me', {}, token)
  },
  updateLocale(token: string, preferred_locale: User['preferred_locale']) {
    return request<User>('/auth/me/locale', { method: 'PATCH', body: JSON.stringify({ preferred_locale }) }, token)
  },
  changeOwnPassword(token: string, current_password: string, new_password: string) {
    return request<void>('/auth/me/password', { method: 'POST', body: JSON.stringify({ current_password, new_password }) }, token)
  },
  dashboard(token: string) {
    return request<DashboardOverview>('/dashboard', {}, token)
  },
  async downloadTemplate(token: string) {
    return download('/admin/pre-registrations/template', { method: 'GET' }, token)
  },
  async importPreRegistrations(token: string, file: File) {
    const form = new FormData()
    form.append('file', file)
    return download('/admin/pre-registrations/import', { method: 'POST', body: form }, token, false)
  },
  preRegistrations(token: string, options: { role?: 'student' | 'mentor'; account_status?: 'issued' | 'activated' | 'revoked'; search?: string } = {}) {
    const query = new URLSearchParams({ ...(options.role ? { role: options.role } : {}), ...(options.account_status ? { account_status: options.account_status } : {}), ...(options.search ? { search: options.search } : {}) })
    return request<PreRegistrationAccountListResponse>(`/admin/pre-registrations?${query.toString()}`, {}, token)
  },
  deletePreRegistration(token: string, preRegistrationId: string) {
    return request<void>(`/admin/pre-registrations/${preRegistrationId}`, { method: 'DELETE' }, token)
  },
  deletePreRegistrations(token: string, ids: string[]) {
    return request<void>('/admin/pre-registrations/bulk-delete', { method: 'POST', body: JSON.stringify({ ids }) }, token)
  },
  completeStudentRegistration(token: string, payload: StudentAcademicProfile) {
    return request<AuthResponse>('/profiles/student/complete-registration', { method: 'POST', body: JSON.stringify(payload) }, token)
  },
  completeMentorRegistration(token: string, payload: MentorAcademicProfile) {
    return request<AuthResponse>('/profiles/mentor/complete-registration', { method: 'POST', body: JSON.stringify(payload) }, token)
  },
  studentProfile(token: string) {
    return request<AcademicProfileResponse>('/profiles/student/me', {}, token)
  },
  mentorProfile(token: string) {
    return request<AcademicProfileResponse>('/profiles/mentor/me', {}, token)
  },
  updateStudentProfile(token: string, payload: StudentAcademicProfile) {
    return request<AcademicProfileResponse>('/profiles/student/me', { method: 'PUT', body: JSON.stringify(payload) }, token)
  },
  updateMentorProfile(token: string, payload: MentorAcademicProfile) {
    return request<AcademicProfileResponse>('/profiles/mentor/me', { method: 'PUT', body: JSON.stringify(payload) }, token)
  },
  mentorRecommendations(token: string) {
    return request<MentorRecommendationListResponse>('/matching/mentors', {}, token)
  },
  studentCandidates(token: string) {
    return request<StudentCandidateListResponse>('/matching/students', {}, token)
  },
  studentSelections(token: string) {
    return request<MentorSelection[]>('/selection/student/me', {}, token)
  },
  chooseMentor(token: string, mentorId: string, note?: string) {
    return request<MentorSelection>(`/selection/student/mentors/${mentorId}`, { method: 'POST', body: JSON.stringify({ note }) }, token)
  },
  cancelMentorChoice(token: string, selectionId: string) {
    return request<void>(`/selection/student/selections/${selectionId}/cancel`, { method: 'POST' }, token)
  },
  mentorSelectionSettings(token: string) {
    return request<MentorSelectionSettings>('/selection/mentor/settings', {}, token)
  },
  updateMentorSelectionSettings(token: string, payload: { capacity?: number; selection_mode?: 'manual' | 'first_come' }) {
    return request<MentorSelectionSettings>('/selection/mentor/settings', { method: 'PATCH', body: JSON.stringify(payload) }, token)
  },
  mentorSelectionCandidates(token: string) {
    return request<SelectionCandidateListResponse>('/selection/mentor/candidates', {}, token)
  },
  inviteStudent(token: string, studentId: string, note?: string) {
    return request<MentorSelection>(`/selection/mentor/students/${studentId}/invite`, { method: 'POST', body: JSON.stringify({ note }) }, token)
  },
  confirmSelection(token: string, selectionId: string, note?: string) {
    return request<MentorSelection>(`/selection/mentor/selections/${selectionId}/confirm`, { method: 'POST', body: JSON.stringify({ note }) }, token)
  },
  rejectSelection(token: string, selectionId: string, note?: string) {
    return request<MentorSelection>(`/selection/mentor/selections/${selectionId}/reject`, { method: 'POST', body: JSON.stringify({ note }) }, token)
  },
  selectionSettings(token: string) {
    return request<SelectionSettings>('/admin/selection/settings', {}, token)
  },
  updateSelectionSettings(token: string, payload: Partial<SelectionSettings>) {
    return request<SelectionSettings>('/admin/selection/settings', { method: 'PATCH', body: JSON.stringify(payload) }, token)
  },
  adminSelectionUsers(token: string, role: 'student' | 'mentor') {
    return request<AdminSelectionUser[]>(`/admin/selection/users?role=${role}`, {}, token)
  },
  updateAdminSelectionUser(token: string, userId: string, payload: { choice_limit?: number; capacity?: number; is_exempt?: boolean; selection_mode?: 'manual' | 'first_come'; use_default?: boolean }) {
    return request<AdminSelectionUser>(`/admin/selection/users/${userId}`, { method: 'PATCH', body: JSON.stringify(payload) }, token)
  },
  adminSelectionRecords(token: string, options: { selection_status?: string; search?: string } = {}) {
    const query = new URLSearchParams({ ...(options.selection_status ? { selection_status: options.selection_status } : {}), ...(options.search ? { search: options.search } : {}) })
    return request<AdminSelectionRecordListResponse>(`/admin/selection/records?${query.toString()}`, {}, token)
  },
  releaseAdminSelectionRecord(token: string, selectionId: string) {
    return request<void>(`/admin/selection/records/${selectionId}/release`, { method: 'POST' }, token)
  },
  releaseAdminSelectionRecords(token: string, selectionIds: string[]) {
    return request<void>('/admin/selection/records/bulk-release', { method: 'POST', body: JSON.stringify({ selection_ids: selectionIds }) }, token)
  },
  resources(token: string, resourceType?: ResourceType, search = '') {
    const query = new URLSearchParams({ ...(resourceType ? { resource_type: resourceType } : {}), ...(search ? { search } : {}) })
    return request<LearningResourceListResponse>(`/resources?${query.toString()}`, {}, token)
  },
  recommendedResources(token: string, limit = 6) {
    return request<LearningResourceListResponse>(`/resources/recommended?limit=${limit}`, {}, token)
  },
  downloadResource(token: string, resourceId: string) {
    return download(`/resources/${resourceId}/download`, { method: 'GET' }, token)
  },
  mentorResourceQuota(token: string) {
    return request<MentorResourceQuota>('/mentor/resources/quota', {}, token)
  },
  mentorResources(token: string) {
    return request<LearningResourceListResponse>('/mentor/resources', {}, token)
  },
  uploadMentorResource(token: string, payload: FormData) {
    return upload<LearningResource>('/mentor/resources', payload, token)
  },
  deleteMentorResource(token: string, resourceId: string) {
    return request<void>(`/mentor/resources/${resourceId}`, { method: 'DELETE' }, token)
  },
  adminResourceQuotas(token: string, search = '') {
    const query = new URLSearchParams({ ...(search ? { search } : {}) })
    return request<AdminResourceQuotaListResponse>(`/admin/resource-quotas?${query.toString()}`, {}, token)
  },
  updateAdminResourceQuota(token: string, userId: string, quota_mb: number) {
    return request<MentorResourceQuota>(`/admin/resource-quotas/${userId}`, { method: 'PATCH', body: JSON.stringify({ quota_mb }) }, token)
  },
  managedUsers(token: string, role: 'student' | 'mentor', search = '') {
    const query = new URLSearchParams({ role, ...(search ? { search } : {}) })
    return request<ManagedUserListResponse>(`/admin/users?${query.toString()}`, {}, token)
  },
  updateManagedUser(token: string, userId: string, payload: AdminUserUpdatePayload) {
    return request<ManagedUser>(`/admin/users/${userId}`, { method: 'PATCH', body: JSON.stringify(payload) }, token)
  },
  resetManagedUserPassword(token: string, userId: string, newPassword: string) {
    return request<void>(`/admin/users/${userId}/password`, { method: 'POST', body: JSON.stringify({ new_password: newPassword }) }, token)
  },
  updateManagedUsersStatus(token: string, user_ids: string[], is_active: boolean) {
    return request<{ updated: number }>('/admin/users/batch-status', { method: 'POST', body: JSON.stringify({ user_ids, is_active }) }, token)
  },
  aiQuota(token: string) {
    return request<AiQuota>('/ai/quota', {}, token)
  },
  aiConversations(token: string) {
    return request<AiConversation[]>('/ai/conversations', {}, token)
  },
  createAiConversation(token: string, topic: AiTopic, title?: string) {
    return request<AiConversation>('/ai/conversations', { method: 'POST', body: JSON.stringify({ topic, title }) }, token)
  },
  aiConversation(token: string, conversationId: string) {
    return request<AiConversationDetail>(`/ai/conversations/${conversationId}`, {}, token)
  },
  sendAiMessage(token: string, conversationId: string, content: string) {
    return request<AiChatResponse>(`/ai/conversations/${conversationId}/messages`, { method: 'POST', body: JSON.stringify({ content }) }, token)
  },
  adminAiQuotas(token: string, role?: 'student' | 'mentor', search = '') {
    const query = new URLSearchParams({ ...(role ? { role } : {}), ...(search ? { search } : {}) })
    return request<AdminAiQuotaListResponse>(`/admin/ai/quotas?${query.toString()}`, {}, token)
  },
  updateAdminAiQuota(token: string, userId: string, payload: { daily_limit?: number; credit_balance?: number; daily_used?: number; plan_code?: string }) {
    return request<AiQuota>(`/admin/ai/quotas/${userId}`, { method: 'PATCH', body: JSON.stringify(payload) }, token)
  },
}

async function download(path: string, init: RequestInit, token: string, includeJsonHeader = true) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      ...(includeJsonHeader ? { 'Content-Type': 'application/json' } : {}),
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
  })
  if (!response.ok) {
    throw await responseError(response)
  }
  return {
    blob: await response.blob(),
    filename: response.headers.get('Content-Disposition')?.match(/filename="?([^";]+)"?/)?.[1] || 'download.xlsx',
    count: response.headers.get('X-Pre-Registration-Count'),
  }
}

async function upload<T>(path: string, form: FormData, token: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { method: 'POST', body: form, headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw await responseError(response)
  return response.json() as Promise<T>
}
