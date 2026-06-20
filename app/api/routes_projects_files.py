from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.db.database import get_db
from app.models.project_file import ProjectFile
from app.models.project import Project

router = APIRouter(prefix="/project-files", tags=["Project Files"])


class ProjectFileCreate(BaseModel):
    project_id: int
    uploaded_by: int | None = None
    original_name: str
    storage_path: str
    mime_type: str | None = None
    ext: str | None = None
    project_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None


class ProjectFileUpdate(BaseModel):
    original_name: str | None = None
    is_deleted: bool | None = None


def serialize_file(f: ProjectFile):
    return {
        "id": f.id,
        "project_id": f.project_id,
        "uploaded_by": f.uploaded_by,
        "original_name": f.original_name,
        "storage_path": f.storage_path,
        "mime_type": f.mime_type,
        "ext": f.ext,
        "project_type": f.project_type,
        "size_bytes": f.size_bytes,
        "checksum": f.checksum,
        "is_deleted": f.is_deleted,
        "created_at": f.created_at,
        "updated_at": f.updated_at,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_file(payload: ProjectFileCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file = ProjectFile(
        project_id=payload.project_id,
        uploaded_by=payload.uploaded_by,
        original_name=payload.original_name.strip(),
        storage_path=payload.storage_path,
        mime_type=payload.mime_type,
        ext=payload.ext,
        project_type=payload.project_type or "N/A",
        size_bytes=payload.size_bytes,
        checksum=payload.checksum,
        is_deleted=False,
    )

    db.add(file)

    project.file_count_cached += 1
    project.last_file_at_cached = file.created_at

    db.commit()
    db.refresh(file)

    return serialize_file(file)


@router.get("/", response_model=List[dict])
def list_files(db: Session = Depends(get_db)):
    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.is_deleted.is_(False))
        .order_by(ProjectFile.created_at.desc())
        .all()
    )

    return [serialize_file(f) for f in files]


@router.get("/project/{project_id}", response_model=List[dict])
def list_files_by_project(project_id: int, db: Session = Depends(get_db)):
    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id, ProjectFile.is_deleted.is_(False))
        .order_by(ProjectFile.created_at.desc())
        .all()
    )

    return [serialize_file(f) for f in files]


@router.get("/{file_id}")
def get_file(file_id: int, db: Session = Depends(get_db)):
    file = (
        db.query(ProjectFile)
        .filter(ProjectFile.id == file_id, ProjectFile.is_deleted.is_(False))
        .first()
    )

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return serialize_file(file)


@router.put("/{file_id}")
def update_file(
    file_id: int, payload: ProjectFileUpdate, db: Session = Depends(get_db)
):
    file = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if payload.original_name is not None:
        file.original_name = payload.original_name.strip()

    if payload.is_deleted is not None:
        if file.is_deleted is False and payload.is_deleted is True:
            project = db.query(Project).filter(Project.id == file.project_id).first()
            if project and project.file_count_cached > 0:
                project.file_count_cached -= 1
        file.is_deleted = payload.is_deleted

    db.commit()
    db.refresh(file)

    return serialize_file(file)


@router.delete("/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file.is_deleted is False:
        project = db.query(Project).filter(Project.id == file.project_id).first()
        if project and project.file_count_cached > 0:
            project.file_count_cached -= 1

    file.is_deleted = True

    db.commit()

    return {"status": "deleted"}
