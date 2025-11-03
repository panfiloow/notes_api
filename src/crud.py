from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .schemas import Note, CreateNote, UpdateNote
from .database import get_db 
from .models import Note as NoteModel
from datetime import datetime


router = APIRouter(
    prefix="/notes",
    tags=["notes"]
)

@router.post("/", response_model=Note, status_code=status.HTTP_201_CREATED) 
async def create_note(
    note: CreateNote, 
    db: AsyncSession = Depends(get_db)
): 
    db_note = NoteModel(
        title=note.title,
        content=note.content,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(db_note)
    await db.commit() 
    await db.refresh(db_note)
    return db_note

@router.get("/", response_model=list[Note])
async def get_notes(
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=100), 
    db: AsyncSession = Depends(get_db)
):
    stmt = select(NoteModel).offset(skip).limit(limit)
    result = await db.execute(stmt)
    notes = result.scalars().all()
    return notes

@router.get("/{note_id}", response_model=Note)
async def get_note_by_id(note_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(NoteModel).where(NoteModel.id == note_id)
    result = await db.execute(stmt)
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail=f"Note with id {note_id} not found")
    return note

@router.put("/{note_id}", response_model=Note)
async def update_note(
    note_id: int,
    note_update: UpdateNote,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(NoteModel).where(NoteModel.id == note_id)
    result = await db.execute(stmt)
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail=f"Note with id {note_id} not found")
    
    if note_update.title is not None:
        note.title = note_update.title
    if note_update.content is not None:
        note.content = note_update.content
    
    note.updated_at = datetime.now()
    await db.commit()
    await db.refresh(note) 

    return note

@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db) 
):
    stmt_check = select(NoteModel).where(NoteModel.id == note_id)
    result_check = await db.execute(stmt_check)
    note_to_delete = result_check.scalar_one_or_none()
    if not note_to_delete:
        raise HTTPException(status_code=404, detail=f"Note with id {note_id} not found")
    await db.delete(note_to_delete) 
    await db.commit()
