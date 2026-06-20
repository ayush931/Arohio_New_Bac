from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
from app.db.database import get_db
from app.models.project import Project

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectCreate(BaseModel):
    owner_id: int
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_archived: bool | None = None


def serialize_project(p: Project):
    return {
        "id": p.id,
        "owner_id": p.owner_id,
        "name": p.name,
        "description": p.description,
        "is_archived": p.is_archived,
        "file_count_cached": p.file_count_cached,
        "last_file_at_cached": p.last_file_at_cached,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    existing = db.query(Project).filter(
        Project.owner_id == payload.owner_id,
        Project.name.ilike(payload.name.strip())
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Project already exists")

    now = datetime.utcnow()
    project = Project(
        owner_id=payload.owner_id,
        name=payload.name.strip(),
        description=payload.description,
        is_archived=False,
        created_at=now,
        updated_at=now
    )

    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize_project(project)


@router.get("/", response_model=List[dict])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    return [serialize_project(p) for p in projects]


@router.get("/user/{user_id}", response_model=List[dict])
def list_projects_by_user(user_id: int, db: Session = Depends(get_db)):
    projects = db.query(Project).filter(
        Project.owner_id == user_id,
        Project.is_archived.is_(False)
    ).order_by(Project.updated_at.desc()).all()
    return [serialize_project(p) for p in projects]


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return serialize_project(project)


@router.put("/{project_id}")
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.description is not None:
        project.description = payload.description
    if payload.is_archived is not None:
        project.is_archived = payload.is_archived

    project.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(project)
    return serialize_project(project)


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"status": "deleted"}