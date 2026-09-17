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
  AiModelTier,
  AiQuota,
  AiResponseMode,
  AiTopic,
  InstitutionAdminScope,
  InstitutionAccount,
  InstitutionOption,
  InstitutionSubscriptionAllocation,
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
  PremiumSubscriptionKey,
  PremiumSubscriptionPlan,
  SubscriptionKeyDeliveryValidation,
  MentorSelection,
  MentorSelectionSettings,
  SelectionCandidateListResponse,
  SelectionSettings,
  AdminSelectionUser,
  AdminSelectionRecordListResponse,
  PreRegistrationAccountListResponse,
  User,
  UserSubscription,
} from '@/types/auth'

const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export class ApiError extends Error {
  constructor(message: string, public readonly details: string[] = [], public readonly code?: string, public readonly status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function responseError(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null)
  const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : undefined
  const fallback = `Request failed (${response.status})`
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item: unknown) => {
      if (typeof item === 'string') return [item]
      if (item && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string') {
        const path = 'loc' in item && Array.isArray(item.loc)
          ? item.loc.filter(part => typeof part === 'string' || typeof part === 'number').filter(part => part !== 'body').join('.')
          : ''
        return [path ? `${path}: ${item.msg}` : item.msg]
      }
      return []
    })
    return new ApiError(messages.join('\n') || fallback, messages, undefined, response.status)
  }
  if (detail && typeof detail === 'object' && 'code' in detail && typeof detail.code === 'string') {
    return new ApiError(detail.code, [], detail.code, response.status)
  }
  return new ApiError(typeof detail === 'string' ? detail : fallback, [], undefined, response.status)
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
  updateContact(token: string, contact: { phone: string; email: string }) {
    return request<User>('/auth/me/contact', { method: 'PATCH', body: JSON.stringify(contact) }, token)
  },
  changeOwnPassword(token: string, current_password: string, new_password: string) {
    return request<AuthResponse>('/auth/me/password', { method: 'POST', body: JSON.stringify({ current_password, new_password }) }, token)
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
  completeStudentRegistration(token: string, payload: StudentAcademicProfile, contact: { phone: string; email: string }) {
    return request<AuthResponse>('/profiles/student/complete-registration', { method: 'POST', body: JSON.stringify({ ...payload, ...contact }) }, token)
  },
  completeMentorRegistration(token: string, payload: MentorAcademicProfile, contact: { phone: string; email: string }) {
    return request<AuthResponse>('/profiles/mentor/complete-registration', { method: 'POST', body: JSON.stringify({ ...payload, ...contact }) }, token)
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
  createAiConversation(token: string, topic: AiTopic) {
    return request<AiConversation>('/ai/conversations', { method: 'POST', body: JSON.stringify({ topic }) }, token)
  },
  renameAiConversation(token: string, conversationId: string, title: string) {
    return request<AiConversation>(`/ai/conversations/${conversationId}`, { method: 'PATCH', body: JSON.stringify({ title }) }, token)
  },
  deleteAiConversation(token: string, conversationId: string) {
    return request<void>(`/ai/conversations/${conversationId}`, { method: 'DELETE' }, token)
  },
  aiConversation(token: string, conversationId: string) {
    return request<AiConversationDetail>(`/ai/conversations/${conversationId}`, {}, token)
  },
  sendAiMessage(token: string, conversationId: string, content: string, options: { model_tier: AiModelTier; response_mode: AiResponseMode }) {
    return request<AiChatResponse>(`/ai/conversations/${conversationId}/messages`, { method: 'POST', body: JSON.stringify({ content, ...options }) }, token)
  },
  async sendAiMessageStream(token: string, conversationId: string, content: string, model_tier: AiModelTier, onText: (text: string) => void): Promise<AiChatResponse> {
    const response = await fetch(`${baseUrl}/ai/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ content, model_tier, response_mode: 'stream' }),
    })
    if (!response.ok) throw await responseError(response)
    if (!response.body) throw new ApiError('Streaming response body is unavailable')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let completed: AiChatResponse | null = null
    try {
      while (true) {
        const { done, value } = await reader.read()
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
        const events = buffer.split(/\r?\n\r?\n/)
        buffer = events.pop() || ''
        for (const rawEvent of events) {
          const lines = rawEvent.split(/\r?\n/)
          const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim()
          const rawData = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
          if (!event || !rawData) continue
          const data = JSON.parse(rawData) as { text?: string; code?: string } | AiChatResponse
          if (event === 'text' && 'text' in data && data.text) onText(data.text)
          if (event === 'error' && 'code' in data) throw new ApiError(data.code || 'Streaming request failed', [], data.code)
          if (event === 'done') {
            completed = data as AiChatResponse
            return completed
          }
        }
        if (done) break
      }
      if (!completed) throw new ApiError('Streaming response ended without a completion event')
      return completed
    } finally {
      await reader.cancel().catch(() => undefined)
      reader.releaseLock()
    }
  },
  adminAiQuotas(token: string, role?: 'student' | 'mentor', search = '') {
    const query = new URLSearchParams({ ...(role ? { role } : {}), ...(search ? { search } : {}) })
    return request<AdminAiQuotaListResponse>(`/admin/ai/quotas?${query.toString()}`, {}, token)
  },
  updateAdminAiQuota(token: string, userId: string, payload: { daily_limit?: number; credit_balance?: number; daily_used?: number; plan_code?: string }) {
    return request<AiQuota>(`/admin/ai/quotas/${userId}`, { method: 'PATCH', body: JSON.stringify(payload) }, token)
  },
  subscription(token: string) {
    return request<UserSubscription>('/subscriptions/me', {}, token)
  },
  activateSubscriptionKey(token: string, key: string) {
    return request<UserSubscription>('/subscriptions/activate', { method: 'POST', body: JSON.stringify({ key }) }, token)
  },
  subscriptionAllocations(token: string) {
    return request<InstitutionSubscriptionAllocation[]>('/admin/subscriptions/allocations', {}, token)
  },
  subscriptionInstitutions(token: string) {
    return request<InstitutionOption[]>('/admin/subscriptions/institutions', {}, token)
  },
  institutionAccounts(token: string, institutionAbbr: string) {
    return request<InstitutionAccount[]>(`/admin/subscriptions/institutions/${encodeURIComponent(institutionAbbr)}/accounts`, {}, token)
  },
  saveSubscriptionAllocation(token: string, institutionAbbr: string, payload: Pick<InstitutionSubscriptionAllocation, 'pro_credits' | 'ultra_credits' | 'max_credits'>) {
    return request<InstitutionSubscriptionAllocation>(`/admin/subscriptions/allocations/${encodeURIComponent(institutionAbbr)}`, { method: 'PUT', body: JSON.stringify(payload) }, token)
  },
  institutionAdminScopes(token: string) {
    return request<InstitutionAdminScope[]>('/admin/subscriptions/institution-admins', {}, token)
  },
  myInstitutionAdminScopes(token: string) {
    return request<InstitutionAdminScope[]>('/admin/subscriptions/my-scopes', {}, token)
  },
  assignInstitutionAdmin(token: string, payload: { user_id: string; institution_abbr: string }) {
    return request<InstitutionAdminScope>('/admin/subscriptions/institution-admins', { method: 'POST', body: JSON.stringify(payload) }, token)
  },
  removeInstitutionAdmin(token: string, scopeId: string) {
    return request<void>(`/admin/subscriptions/institution-admins/${scopeId}`, { method: 'DELETE' }, token)
  },
  premiumSubscriptionKeys(token: string) {
    return request<PremiumSubscriptionKey[]>('/admin/subscriptions/keys', {}, token)
  },
  issuePremiumSubscriptionKeysReceipt(token: string, payload: { institution_abbr: string; plan_code: PremiumSubscriptionPlan; quantity: number }) {
    return download('/admin/subscriptions/keys/batch', { method: 'POST', body: JSON.stringify(payload) }, token)
  },
  revokePremiumSubscriptionKey(token: string, keyId: string) {
    return request<PremiumSubscriptionKey>(`/admin/subscriptions/keys/${keyId}`, { method: 'DELETE' }, token)
  },
  validateSubscriptionDeliveryReceipt(token: string, file: File) {
    const form = new FormData()
    form.append('file', file)
    return upload<SubscriptionKeyDeliveryValidation[]>('/admin/subscription-delivery/validate-excel', form, token)
  },
  directlyActivateSubscriptionDelivery(token: string, items: { key: string; recipient_user_id?: string }[]) {
    return request<{ activated_count: number }>('/admin/subscription-delivery/activate', { method: 'POST', body: JSON.stringify({ items }) }, token)
  },
  exportSubscriptionDeliveryPdfs(token: string, items: { key: string; recipient_user_id?: string }[]) {
    return download('/admin/subscription-delivery/export-pdf', { method: 'POST', body: JSON.stringify({ items }) }, token)
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
    subscriptionKeyCount: response.headers.get('X-Subscription-Key-Count'),
  }
}

async function upload<T>(path: string, form: FormData, token: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { method: 'POST', body: form, headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw await responseError(response)
  return response.json() as Promise<T>
}
