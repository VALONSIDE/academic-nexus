export type Role = 'student' | 'mentor' | 'admin' | 'super_admin' | 'institution_admin'
export type Locale = 'zh-CN' | 'en-US'

export interface User {
  id: string
  username: string
  full_name: string
  phone: string | null
  email: string | null
  preferred_locale: Locale
  is_active: boolean
  roles: Role[]
}

export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
  user: User
}

export interface ActivationStartResponse {
  registration_token: string
  token_type: 'bearer'
  role: 'student' | 'mentor'
}

export interface LoginPayload {
  username: string
  password: string
}

export interface ActivationPayload extends LoginPayload {
  full_name: string
  academic_id: string
  access_key: string
  preferred_locale: Locale
  terms_accepted: true
  privacy_accepted: true
}

export interface StudentAcademicProfile {
  research_interests: string[]
  skills: string[]
  academic_performance: string
  academic_goals: string
  research_experience: string
}

export interface MentorAcademicProfile {
  research_directions: string[]
  representative_papers: string[]
  research_projects: string
  mentoring_style: string
}

export interface AcademicProfileResponse {
  role: 'student' | 'mentor'
  profile_completed: boolean
  completed_at: string | null
  data: StudentAcademicProfile | MentorAcademicProfile
}

export interface ManagedUser extends User {
  role: 'student' | 'mentor'
  phone: string | null
  academic_id: string | null
  institution_abbr: string | null
  institution_name_zh: string | null
  college_name_zh: string | null
  profile_completed: boolean
  profile: StudentAcademicProfile | MentorAcademicProfile
}

export interface ManagedUserListResponse {
  items: ManagedUser[]
  total: number
}

export interface PreRegistrationAccount {
  id: string
  batch_id: string
  username: string
  role_code: 'student' | 'mentor'
  full_name: string
  academic_id: string
  institution_abbr: string
  institution_name_zh: string
  college_name_zh: string
  status: 'issued' | 'activated' | 'revoked'
  created_at: string
  activated_at: string | null
}

export interface PreRegistrationAccountListResponse {
  items: PreRegistrationAccount[]
  total: number
}

export interface AdminUserUpdatePayload {
  full_name?: string
  phone?: string
  email?: string
  preferred_locale?: Locale
  is_active?: boolean
  student_profile?: StudentAcademicProfile
  mentor_profile?: MentorAcademicProfile
}

export type AiTopic = 'academic_planning' | 'mentor_consultation' | 'learning_roadmap' | 'selection_advisor'
export type AiModelTier = 'light' | 'standard' | 'expert'
export type AiResponseMode = 'standard' | 'stream'

export interface AiQuota {
  plan_code: string
  daily_limit: number
  daily_used: number
  daily_remaining: number
  credit_balance: number
  project_daily_limit: number
  project_daily_used: number
  project_daily_remaining: number
  cycle_started_at: string
  cycle_ends_at: string
  cycle_credit_limit: number
  cycle_credits_used: number
}

export interface AiMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface AiConversation {
  id: string
  topic: AiTopic
  title: string
  last_message_at: string | null
  created_at: string
}

export interface AiConversationDetail extends AiConversation {
  messages: AiMessage[]
}

export type SubscriptionPlan = 'basic' | 'pro' | 'ultra' | 'max'
export type PremiumSubscriptionPlan = Exclude<SubscriptionPlan, 'basic'>

export interface UserSubscription {
  plan_code: SubscriptionPlan
  credit_limit: number
  credit_balance: number
  credits_used: number
  cycle_started_at: string
  cycle_ends_at: string
}

export interface InstitutionSubscriptionAllocation {
  institution_abbr: string
  institution_name_zh: string
  pro_credits: number
  ultra_credits: number
  max_credits: number
}

export interface InstitutionOption {
  institution_abbr: string
  institution_name_zh: string
}

export interface InstitutionAccount {
  id: string
  username: string
  full_name: string
  role: 'student' | 'mentor'
  has_active_premium_subscription: boolean
}

export interface InstitutionAdminScope {
  id: string
  user_id: string
  username: string
  full_name: string
  institution_abbr: string
  institution_name_zh: string
  created_at: string
}

export interface PremiumSubscriptionKey {
  id: string
  institution_abbr: string
  institution_name_zh: string
  plan_code: PremiumSubscriptionPlan
  status: 'issued' | 'activated' | 'revoked'
  issued_at: string
  activated_at: string | null
  revoked_at: string | null
}

export interface SubscriptionKeyDeliveryValidation {
  row_number: number
  key: string
  plan_code: PremiumSubscriptionPlan | null
  institution_abbr: string | null
  institution_name_zh: string | null
  status: 'available' | 'invalid' | 'unavailable' | 'not_authorized'
}

export interface AiChatResponse {
  user_message: AiMessage
  assistant_message: AiMessage
  quota: AiQuota
}

export interface AdminAiQuotaUser {
  user_id: string
  username: string
  full_name: string
  role: 'student' | 'mentor'
  plan_code: string
  daily_limit: number
  daily_used: number
  credit_balance: number
}

export interface AdminAiQuotaListResponse {
  items: AdminAiQuotaUser[]
  total: number
  project_daily_limit: number
  project_daily_used: number
  project_daily_remaining: number
}

export type MatchFactorCode = 'research_alignment' | 'skills_alignment' | 'development_alignment'

export interface MatchFactor {
  code: MatchFactorCode
  score: number
  shared_terms: string[]
}

export interface MatchedMentor {
  user_id: string
  username: string
  full_name: string
  university: string | null
  department: string | null
  same_college: boolean
  title: string | null
  research_directions: string[]
  representative_papers: string[]
  research_projects: string | null
  mentoring_style: string | null
  match_score: number
  factors: MatchFactor[]
}

export interface MatchedStudent {
  user_id: string
  username: string
  full_name: string
  university: string | null
  department: string | null
  same_college: boolean
  major: string | null
  grade: string | null
  research_interests: string[]
  skills: string[]
  academic_performance: string | null
  academic_goals: string | null
  research_experience: string | null
  match_score: number
  factors: MatchFactor[]
}

export interface MentorRecommendationListResponse {
  algorithm_version: string
  ranking_mode: 'local' | 'semantic' | 'hybrid'
  total: number
  items: MatchedMentor[]
}

export interface StudentCandidateListResponse {
  algorithm_version: string
  ranking_mode: 'local' | 'semantic' | 'hybrid'
  total: number
  items: MatchedStudent[]
}

export type ResourceType = 'course' | 'paper' | 'book'

export interface LearningResource {
  id: string
  resource_type: ResourceType
  title: string
  description: string
  topics: string[]
  tags: string[]
  external_url: string | null
  file_original_name: string | null
  file_size_bytes: number
  download_url: string | null
  owner_name: string
  created_at: string
  metadata: Record<string, string | number | null>
  recommendation_score: number | null
}

export interface LearningResourceListResponse {
  ranking_mode?: 'local' | 'semantic' | 'hybrid' | null
  items: LearningResource[]
  total: number
}

export interface MentorResourceQuota {
  quota_bytes: number
  used_bytes: number
  remaining_bytes: number
}

export interface AdminResourceQuotaUser extends MentorResourceQuota {
  user_id: string
  username: string
  full_name: string
}

export interface AdminResourceQuotaListResponse {
  items: AdminResourceQuotaUser[]
  total: number
}

export interface DashboardMetric {
  code: string
  value: number
  total: number | null
}

export interface DashboardBreakdown {
  code: string
  value: number
}

export interface DashboardOverview {
  role: Role
  metrics: DashboardMetric[]
  profile_completion: DashboardBreakdown[]
  resource_distribution: DashboardBreakdown[]
  selection_statistics: DashboardBreakdown[]
  recent_selection_activity: DashboardSelectionActivity[]
}

export interface DashboardSelectionActivity {
  id: string
  student_name: string
  mentor_name: string
  status: SelectionStatus
  updated_at: string
}

export type SelectionStatus = 'pending_student' | 'pending_mentor' | 'confirmed' | 'rejected' | 'cancelled'
export type SelectionMode = 'manual' | 'first_come'

export interface MentorSelection {
  id: string
  student_user_id: string
  mentor_user_id: string
  status: SelectionStatus
  student_note: string | null
  mentor_note: string | null
  created_at: string
  updated_at: string
  confirmed_at: string | null
}

export interface MentorSelectionSettings {
  capacity: number
  is_exempt: boolean
  selection_mode: SelectionMode
  confirmed_count: number
  invitation_count: number
  available_slots: number
}

export interface SelectionCandidate {
  selection: MentorSelection
  full_name: string
  username: string
  university: string | null
  department: string | null
  major: string | null
  research_interests: string[]
  skills: string[]
  match_score: number
}

export interface SelectionCandidateListResponse {
  settings: MentorSelectionSettings
  items: SelectionCandidate[]
}

export interface SelectionSettings {
  is_open: boolean
  default_capacity: number
  default_student_choice_limit: number
}

export interface AdminSelectionUser {
  user_id: string
  username: string
  full_name: string
  role: 'student' | 'mentor'
  institution_name_zh: string | null
  college_name_zh: string | null
  choice_limit: number | null
  capacity: number | null
  is_exempt: boolean
  selection_mode: SelectionMode | null
}

export interface AdminSelectionRecord {
  id: string
  status: SelectionStatus
  student_user_id: string
  student_name: string
  student_username: string
  student_institution_name_zh: string | null
  student_college_name_zh: string | null
  mentor_user_id: string
  mentor_name: string
  mentor_username: string
  mentor_institution_name_zh: string | null
  mentor_college_name_zh: string | null
  created_at: string
  updated_at: string
  confirmed_at: string | null
}

export interface AdminSelectionRecordListResponse {
  items: AdminSelectionRecord[]
  total: number
}
