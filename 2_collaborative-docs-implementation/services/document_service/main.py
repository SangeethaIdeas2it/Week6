import os
from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from passlib.context import CryptContext
from pydantic import BaseModel, constr
from typing import Optional, List
import aioredis
import logging
import uvicorn
from datetime import datetime
import io

# --- Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/collabdocs")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# --- Database Setup ---
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# --- Redis Setup ---
redis = None

# --- Models ---
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    search_vector = Column(TSVECTOR)

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentPermission(Base):
    __tablename__ = "document_permissions"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    permission = Column(String, nullable=False)  # read, write, admin

# --- Pydantic Schemas ---
class DocumentCreate(BaseModel):
    title: constr(min_length=1)
    content: Optional[str] = None

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class DocumentOut(BaseModel):
    id: int
    owner_id: int
    title: str
    content: Optional[str]
    created_at: datetime
    updated_at: datetime

class DocumentVersionOut(BaseModel):
    version: int
    content: str
    created_at: datetime

class ShareRequest(BaseModel):
    user_id: int
    permission: constr(regex="^(read|write|admin)$")

class CollaboratorOut(BaseModel):
    user_id: int
    permission: str

# --- FastAPI App Setup ---
app = FastAPI(title="Document Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency ---
async def get_db():
    async with async_session() as session:
        yield session

# --- Auth Dependency (integrate with User Service JWT) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_user_id_from_token(token: str):
    # Dummy decode for now; replace with real JWT decode and validation
    import jwt
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None

async def get_current_user_id(token: str = Depends(oauth2_scheme)):
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return int(user_id)

# --- Error Handling ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_SERVER_ERROR", "message": str(exc)}}
    )

# --- Endpoints ---
@app.post("/documents", response_model=DocumentOut)
async def create_document(doc: DocumentCreate, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    new_doc = Document(owner_id=user_id, title=doc.title, content=doc.content)
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    # Create initial version
    version = DocumentVersion(document_id=new_doc.id, version=1, content=doc.content or "")
    db.add(version)
    await db.commit()
    return DocumentOut.from_orm(new_doc)

@app.get("/documents", response_model=List[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id), skip: int = 0, limit: int = 10):
    # Check cache first
    cache_key = f"user_docs:{user_id}:{skip}:{limit}"
    cached = await redis.get(cache_key)
    if cached:
        import json
        return [DocumentOut.parse_obj(d) for d in json.loads(cached)]
    result = await db.execute(
        Document.__table__.select().where(Document.owner_id == user_id, Document.is_deleted == False).offset(skip).limit(limit)
    )
    docs = result.fetchall()
    docs_out = [DocumentOut.from_orm(d) for d in docs]
    # Cache result
    await redis.set(cache_key, str([d.dict() for d in docs_out]), ex=60)
    return docs_out

@app.get("/documents/{id}", response_model=DocumentOut)
async def get_document(id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = await db.get(Document, id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    # Check permissions
    if doc.owner_id != user_id:
        perm = await db.execute(DocumentPermission.__table__.select().where(DocumentPermission.document_id == id, DocumentPermission.user_id == user_id))
        if not perm.scalar():
            raise HTTPException(status_code=403, detail="No access to this document")
    return DocumentOut.from_orm(doc)

@app.put("/documents/{id}", response_model=DocumentOut)
async def update_document(id: int, update: DocumentUpdate, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = await db.get(Document, id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    # Only owner or admin can update
    if doc.owner_id != user_id:
        perm = await db.execute(DocumentPermission.__table__.select().where(DocumentPermission.document_id == id, DocumentPermission.user_id == user_id, DocumentPermission.permission.in_(["write", "admin"])))
        if not perm.scalar():
            raise HTTPException(status_code=403, detail="No write access to this document")
    # Versioning
    latest_version = await db.execute(DocumentVersion.__table__.select().where(DocumentVersion.document_id == id).order_by(DocumentVersion.version.desc()))
    latest = latest_version.first()
    new_version_num = (latest.version if latest else 0) + 1
    version = DocumentVersion(document_id=id, version=new_version_num, content=update.content or doc.content)
    db.add(version)
    # Update doc
    if update.title:
        doc.title = update.title
    if update.content:
        doc.content = update.content
    await db.commit()
    await db.refresh(doc)
    return DocumentOut.from_orm(doc)

@app.delete("/documents/{id}")
async def delete_document(id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = await db.get(Document, id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only owner can delete document")
    doc.is_deleted = True
    await db.commit()
    return {"success": True}

@app.post("/documents/{id}/share")
async def share_document(id: int, req: ShareRequest, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = await db.get(Document, id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only owner can share document")
    # Add or update permission
    perm = await db.execute(DocumentPermission.__table__.select().where(DocumentPermission.document_id == id, DocumentPermission.user_id == req.user_id))
    perm_obj = perm.scalar()
    if perm_obj:
        perm_obj.permission = req.permission
    else:
        db.add(DocumentPermission(document_id=id, user_id=req.user_id, permission=req.permission))
    await db.commit()
    return {"success": True}

@app.get("/documents/{id}/collaborators", response_model=List[CollaboratorOut])
async def get_collaborators(id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = await db.get(Document, id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only owner can view collaborators")
    result = await db.execute(DocumentPermission.__table__.select().where(DocumentPermission.document_id == id))
    perms = result.fetchall()
    return [CollaboratorOut(user_id=p.user_id, permission=p.permission) for p in perms]

@app.get("/documents/search", response_model=List[DocumentOut])
async def search_documents(q: str, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id), skip: int = 0, limit: int = 10):
    # Use PostgreSQL full-text search
    result = await db.execute(
        Document.__table__.select().where(
            Document.owner_id == user_id,
            Document.is_deleted == False,
            func.to_tsvector('english', Document.content).match(q)
        ).offset(skip).limit(limit)
    )
    docs = result.fetchall()
    return [DocumentOut.from_orm(d) for d in docs]

@app.post("/documents/{id}/upload")
async def upload_file(id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = await db.get(Document, id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    # Save file content as new version
    content = (await file.read()).decode()
    latest_version = await db.execute(DocumentVersion.__table__.select().where(DocumentVersion.document_id == id).order_by(DocumentVersion.version.desc()))
    latest = latest_version.first()
    new_version_num = (latest.version if latest else 0) + 1
    version = DocumentVersion(document_id=id, version=new_version_num, content=content)
    db.add(version)
    doc.content = content
    await db.commit()
    await db.refresh(doc)
    return {"success": True}

@app.get("/documents/{id}/download")
async def download_file(id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    doc = await db.get(Document, id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return StreamingResponse(io.BytesIO(doc.content.encode()), media_type="text/plain", headers={"Content-Disposition": f"attachment; filename=doc_{id}.txt"})

# --- Startup/Shutdown Events ---
@app.on_event("startup")
async def startup():
    global redis
    redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Document Service started.")

@app.on_event("shutdown")
async def shutdown():
    await redis.close()
    logger.info("Document Service shutdown.")

# --- Run the app ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
