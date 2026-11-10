from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app import ai
from app.db import DbSession
from app.models import Note
from app.schemas import NoteIn, NoteOut
from app.security import CurrentUser

router = APIRouter(prefix="/notes", tags=["notes"])


def _get_owned_note(db: DbSession, user: CurrentUser, note_id: int) -> Note:
    # Missing and someone else's note look the same: 404, so ids aren't revealed.
    note = db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user.id))
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    return note


@router.get("")
def list_notes(
    db: DbSession,
    user: CurrentUser,
    tag: Annotated[str | None, Query(max_length=50)] = None,
) -> list[NoteOut]:
    # Matches ix_notes_user_id_created_at exactly, so no sort step.
    query = (
        select(Note).where(Note.user_id == user.id).order_by(Note.created_at.desc(), Note.id.desc())
    )
    tag = tag.strip().lower() if tag else None
    if tag:
        # tags @> ARRAY[tag] can use the GIN index; "= ANY(tags)" could not.
        query = query.where(Note.tags.contains([tag]))
    return [NoteOut.model_validate(n) for n in db.scalars(query)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_note(body: NoteIn, db: DbSession, user: CurrentUser) -> NoteOut:
    # summarize() never raises; on failure the note is still saved without AI fields.
    result = ai.summarize(body.title, body.content)
    note = Note(
        user_id=user.id,
        title=body.title,
        content=body.content,
        summary=result.summary if result else None,
        tags=result.tags if result else [],
    )
    db.add(note)
    db.commit()
    db.refresh(note)  # load server-side created_at
    return NoteOut.model_validate(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: DbSession, user: CurrentUser) -> Response:
    db.delete(_get_owned_note(db, user, note_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{note_id}/summarize")
def resummarize_note(note_id: int, db: DbSession, user: CurrentUser) -> NoteOut:
    note = _get_owned_note(db, user, note_id)
    result = ai.summarize(note.title, note.content)
    if result is None:  # leave the note unchanged
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "AI summarization failed, please try again later"
        )
    note.summary, note.tags = result.summary, result.tags
    db.commit()
    return NoteOut.model_validate(note)
