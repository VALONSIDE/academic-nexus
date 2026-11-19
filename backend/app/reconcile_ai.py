"""Refund interrupted requests after all API workers have been stopped.

Run: docker compose stop api nginx
     docker compose run --rm --no-deps api python -m app.reconcile_ai
     docker compose up -d
Never run concurrently with live AI requests.
"""
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.ai import AiUsageEvent, AiTurnRequest, AiMessage
from app.services.ai.quota import release_ai_call


def reconcile():
    with SessionLocal() as db:
        ids = list(db.scalars(select(AiUsageEvent.id).where(AiUsageEvent.status == "reserved")))
        for event_id in ids:
            turn = db.scalar(select(AiTurnRequest).where(AiTurnRequest.event_id == event_id))
            if turn:
                if turn.user_message_id:
                    message = db.get(AiMessage, turn.user_message_id)
                    if message:
                        db.delete(message)
                turn.state = "failed"
                db.commit()
            release_ai_call(db, event_id, error_code="worker_interrupted")
        return len(ids)


if __name__ == "__main__":
    print(f"Reconciled interrupted reservations: {reconcile()}")
