from uuid import UUID
from fastapi import APIRouter
from app.api.deps import CurrentUser, DbSession
from app.services.contacts import load_contact, visible_contact

router = APIRouter(prefix="/contacts", tags=["Same-school contacts / 同校联系"])


@router.get("/{user_id}")
def read_contact(user_id: UUID, current_user: CurrentUser, db: DbSession):
    from fastapi.responses import JSONResponse
    target = load_contact(db, current_user, user_id)
    return JSONResponse(visible_contact(current_user, target), headers={"Cache-Control": "no-store, private"})
