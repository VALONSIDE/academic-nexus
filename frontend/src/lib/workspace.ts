export interface WorkspaceNotification {
  id: string
  kind: string
  workspace: 'student' | 'mentor' | 'admin'
  subject_id: string | null
  institution: string | null
  actor: string | null
  counterpart?: string | null
  details: { counterpart_id?: string; limit?: number; exempt?: boolean; plan?: string; quantity?: number; previous?: number; available?: number; quota_mb?: number }
  created_at: string
  read_at: string | null
}

export interface SubscriptionInventory {
  plan: 'pro' | 'ultra' | 'max'
  available: number
  total_issued: number
  issued: number
  in_use: number
  exhausted: number
  expired: number
  reclaimed: number
}

export interface SubscriptionHistoryEntry {
  id: string
  kind: string
  plan: string | null
  created_at: string
  actor: string | null
  details: WorkspaceNotification['details']
}

export type ReminderCategory = 'quota' | 'allocation' | 'issuance' | 'delivery'
export interface AiActionCard {
  kind: 'mutual_selection'
  action: 'apply' | 'invite' | 'accept_invitation' | 'confirm_application'
  target_id: string
  target_name: string
  state: 'ready' | 'completed'
  selection_id?: string
  result_status?: string
}

export function notificationDestination(item: WorkspaceNotification) {
  if (item.kind === 'institution_admin_assigned') return {path: '/admin'}
  if (item.kind === 'institution_admin_revoked') return {path: `/${item.workspace}`}
  if (item.workspace === 'admin') {
    const path = ['reminder_delivery', 'subscription_delivered'].includes(item.kind)
      ? '/admin/subscription-delivery' : '/admin/subscriptions'
    return { path, query: item.institution ? { institution: item.institution } : {} }
  }
  if (item.kind.startsWith('selection_')) {
    return { path: `/${item.workspace}/matches`, query: item.details.counterpart_id ? { candidate: item.details.counterpart_id } : {} }
  }
  return { path: `/${item.workspace}/${item.kind === 'resource_quota_changed' ? 'resources' : 'subscription'}` }
}
