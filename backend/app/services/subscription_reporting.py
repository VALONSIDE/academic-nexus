from sqlalchemy import JSON, Uuid, literal, select, union_all

from app.models.ai import AiUserQuota, AiUserSubscription
from app.models.subscription import InstitutionSubscriptionAllocation, PremiumSubscriptionKey
from app.models.user import User
from app.models.workspace import WorkspaceEvent
from app.services.subscriptions import _as_utc, utc_now


def inventory(db, tenant_id, institution):
    allocation = db.scalar(select(InstitutionSubscriptionAllocation).where(
        InstitutionSubscriptionAllocation.tenant_id == tenant_id,
        InstitutionSubscriptionAllocation.institution_abbr == institution,
    ))
    plans = {
        plan: {"plan": plan, "available": getattr(allocation, f"{plan}_credits", 0),
               "total_issued": 0, "issued": 0, "in_use": 0, "exhausted": 0, "expired": 0, "reclaimed": 0}
        for plan in ("pro", "ultra", "max")
    }
    key = PremiumSubscriptionKey
    sub = AiUserSubscription
    quota = AiUserQuota
    rows = db.execute(select(key.plan_code, key.status, key.activated_at,
                             sub.plan_code, sub.cycle_started_at, sub.cycle_ends_at, quota.credit_balance)
                      .outerjoin(sub, sub.user_id == key.activated_by_user_id)
                      .outerjoin(quota, quota.user_id == key.activated_by_user_id)
                      .where(key.tenant_id == tenant_id, key.institution_abbr == institution))
    now = utc_now()
    for plan, status, activated, current_plan, start, end, balance in rows:
        item = plans[plan]
        item["total_issued"] += 1
        if status == "issued":
            item["issued"] += 1
        elif status == "revoked":
            item["reclaimed"] += 1
        elif not (activated and start and end and current_plan == plan
                  and _as_utc(start) == _as_utc(activated) and _as_utc(end) > now):
            item["expired"] += 1
        elif balance is not None and balance <= 0:
            item["exhausted"] += 1
        else:
            item["in_use"] += 1
    return list(plans.values())


def history(db, tenant_id, institution, limit, offset):
    key = PremiumSubscriptionKey
    event = WorkspaceEvent
    key_scope = (key.tenant_id == tenant_id, key.institution_abbr == institution)
    history_rows = union_all(
        select(key.id.label("id"), literal("subscription_issued").label("kind"),
               key.plan_code.label("plan"), key.issued_at.label("at"),
               key.issued_by_user_id.label("actor"), literal(None, type_=JSON).label("details")).where(*key_scope),
        select(key.id, literal("subscription_activated"), key.plan_code, key.activated_at,
               key.activated_by_user_id, literal(None, type_=JSON)).where(*key_scope, key.activated_at.is_not(None)),
        select(key.id, literal("subscription_reclaimed"), key.plan_code, key.revoked_at,
               literal(None, type_=Uuid), literal(None, type_=JSON)).where(*key_scope, key.revoked_at.is_not(None),
                   ~select(event.id).where(event.subject_id == key.id, event.kind == "subscription_reclaimed",
                                          event.recipient_id.is_(None)).exists()),
        select(event.id, event.kind, literal(None), event.created_at, event.actor_id, event.details)
        .where(event.tenant_id == tenant_id, event.institution_abbr == institution, event.recipient_id.is_(None),
               event.kind.in_(("subscription_allocation", "subscription_reclaimed", "subscription_delivered", "subscription_exported"))),
    ).subquery()
    rows = db.execute(select(history_rows, User.full_name.label("actor_name"))
                      .outerjoin(User, (User.id == history_rows.c.actor) & (User.tenant_id == tenant_id))
                      .order_by(history_rows.c.at.desc(), history_rows.c.id.desc(), history_rows.c.kind)
                      .limit(limit + 1).offset(offset)).mappings().all()
    return {"more": len(rows) > limit, "items": [
        {"id": row["id"], "kind": row["kind"], "plan": row["plan"] or (row["details"] or {}).get("plan"),
         "created_at": row["at"], "actor": row["actor_name"], "details": row["details"] or {}}
        for row in rows[:limit]
    ]}
