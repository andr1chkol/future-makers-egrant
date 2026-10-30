from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.documents import service
from app.documents.settings import DocumentSettings
from app.platform.access import require_access
from app.platform.contracts import Document, NormalizedDocument, Page, Pagination, Success
from app.platform.database import get_session
from app.platform.errors import DomainError

# Keep protection on the module router as well as the shared assembly boundary.
router = APIRouter(dependencies=[Depends(require_access)])
Database = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.post("/documents", status_code=201, response_model=Success[list[Document]])
def upload_documents(files: Annotated[list[UploadFile], File()], session: Database):
    settings = DocumentSettings()
    if len(files) > settings.max_batch_files:
        raise DomainError("BATCH_LIMIT", 413, "Upload batch has too many files")
    uploads = []
    total_bytes = 0
    try:
        for file in files:
            content = file.file.read(settings.max_bytes + 1)
            if len(content) > settings.max_bytes:
                raise DomainError("UPLOAD_TOO_LARGE", 413, "File exceeds the configured size limit")
            total_bytes += len(content)
            if total_bytes > settings.max_batch_bytes:
                raise DomainError(
                    "BATCH_LIMIT", 413, "Upload batch exceeds the configured size limit"
                )
            uploads.append((file.filename or "document", file.content_type, content))
        return {"data": service.create_documents(session, uploads)}
    finally:
        for file in files:
            file.file.close()


@router.get("/documents", response_model=Page[Document])
def list_documents(session: Database, limit: Limit = 50, offset: Offset = 0):
    service.reconcile_interrupted(session)
    documents, total = service.list_documents(session, limit, offset)
    return {"data": documents, "pagination": Pagination(limit=limit, offset=offset, total=total)}


@router.get("/documents/{id}", response_model=Success[Document])
def get_document(id: UUID, session: Database):
    service.reconcile_interrupted(session)
    return {"data": service.get_document(session, id)}


@router.get(
    "/documents/{id}/content",
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
            "description": "Private content",
        },
    },
)
def get_content(id: UUID, session: Database):
    document, content = service.get_content(session, id)
    # UUID-only disposition avoids header injection; the real filename remains in the DTO.
    disposition = (
        "inline"
        if document.media_type in {"application/pdf", "image/jpeg", "image/png"}
        else "attachment"
    )
    return Response(
        content,
        media_type=document.media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="document-{id}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/documents/{id}/normalized", response_model=Success[NormalizedDocument])
def get_normalized(id: UUID, session: Database):
    return {"data": service.get_normalized(session, id)}


@router.post("/documents/{id}/retries", status_code=202, response_model=Success[Document])
def retry_document(id: UUID, session: Database):
    service.reconcile_interrupted(session)
    return {"data": service.retry_document(session, id)}
