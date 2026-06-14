import io
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pypdf import PdfReader
import docx2txt

from app.infrastructure.cache.semantic_cache import db_pool
from app.infrastructure.embeddings.embedding_service import embedding_service
from app.api.deps import verify_internal_gateway

router = APIRouter()

def extract_text(file_content: bytes, filename: str) -> str:
    ext = filename.split(".")[-1].lower()
    if ext == "pdf":
        pdf = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text
    elif ext in ["docx", "doc"]:
        return docx2txt.process(io.BytesIO(file_content))
    elif ext == "txt":
        return file_content.decode("utf-8", errors="ignore")
    else:
        raise ValueError("Unsupported file type")

def chunk_text(text: str, chunk_size=500, overlap=50) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

@router.post("/upload", dependencies=[Depends(verify_internal_gateway)])
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds maximum limit of 10MB")
        
    filename = file.filename
    try:
        text = extract_text(file_content, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Document text content is empty")

    async with db_pool.acquire() as conn:
        doc_count = await conn.fetchval("SELECT COUNT(*) FROM document_sources WHERE user_id = $1", user_id)
        if doc_count >= 20:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum limit of 20 documents exceeded")

        chunks = chunk_text(text)
        if len(chunks) == 0:
            raise HTTPException(status_code=400, detail="No text chunks generated")

        chunk_count = await conn.fetchval("SELECT COUNT(*) FROM document_chunks WHERE user_id = $1", user_id)
        if chunk_count + len(chunks) > 2000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Adding this document would exceed the maximum limit of 2000 text chunks")

        doc_id = await conn.fetchval(
            "INSERT INTO document_sources (user_id, filename, file_type, status, kb_scope) VALUES ($1, $2, $3, 'processing', 'personal') RETURNING id",
            user_id, filename, filename.split(".")[-1].lower()
        )

        try:
            for chunk in chunks:
                vector = await embedding_service.get_embedding(chunk)
                await conn.execute(
                    """INSERT INTO document_chunks (source_id, user_id, session_id, chunk_text, embedding, kb_scope)
                       VALUES ($1, $2, $3, $4, $5, 'personal')""",
                    doc_id, user_id, session_id, chunk, vector
                )
            
            await conn.execute("UPDATE document_sources SET status = 'completed' WHERE id = $1", doc_id)
        except Exception as e:
            await conn.execute("UPDATE document_sources SET status = 'failed' WHERE id = $1", doc_id)
            raise e

    return {"source_id": str(doc_id), "status": "completed"}

@router.get("", dependencies=[Depends(verify_internal_gateway)])
async def list_documents(user_id: str):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, filename, file_type, status, created_at FROM document_sources WHERE user_id = $1 ORDER BY created_at DESC",
            user_id
        )
        return [
            {
                "id": str(r["id"]),
                "filename": r["filename"],
                "file_type": r["file_type"],
                "status": r["status"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            } for r in rows
        ]

@router.delete("/{id}", dependencies=[Depends(verify_internal_gateway)])
async def delete_document(id: str, user_id: str):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM document_sources WHERE id = $1 AND user_id = $2", id, user_id)
        return {"status": "deleted"}
