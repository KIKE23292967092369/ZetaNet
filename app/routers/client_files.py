"""
Sistema ISP - Router: Archivos de Cliente
Endpoints para subir, listar, descargar y eliminar archivos por cliente.
"""
import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.client_file import ClientFile, FileCategory
from app.schemas.client_file import ClientFileResponse, ClientFileListResponse

router = APIRouter(
    prefix="/v1/clients/{client_id}/files",
    tags=["Archivos de Cliente"],
)

# ── Configuración ──────────────────────────────────────────────
UPLOAD_BASE_DIR = Path("uploads")  # Carpeta raíz de archivos
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_FILES_PER_CLIENT = 20


# ── Helpers ────────────────────────────────────────────────────
def _get_upload_dir(tenant_id: int, client_id: int) -> Path:
    """Retorna la carpeta de uploads para un cliente específico."""
    path = UPLOAD_BASE_DIR / f"tenant_{tenant_id}" / f"client_{client_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _validate_file(file: UploadFile):
    """Valida extensión y tamaño del archivo."""
    if not file.filename:
        raise HTTPException(400, "El archivo no tiene nombre")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Extensión '{ext}' no permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    return ext


async def _get_client_or_404(
    client_id: int, tenant_id: int, db: AsyncSession
) -> Client:
    """Obtiene cliente verificando que pertenezca al tenant."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.tenant_id == tenant_id
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(404, "Cliente no encontrado")
    return client


# ── POST: Subir archivo ───────────────────────────────────────
@router.post("/", response_model=ClientFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_client_file(
    client_id: int,
    file: UploadFile = File(...),
    category: FileCategory = Form(default=FileCategory.OTRO),
    description: Optional[str] = Form(default=None, max_length=255),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Subir un archivo para un cliente.
    - Formatos: JPG, PNG, WEBP, PDF
    - Máximo: 5 MB por archivo
    - Máximo: 20 archivos por cliente
    """
    tenant_id = current_user.tenant_id

    # Validar que el cliente existe y pertenece al tenant
    await _get_client_or_404(client_id, tenant_id, db)

    # Validar archivo
    ext = _validate_file(file)

    # Validar tamaño (leer contenido)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"Archivo excede el máximo de {MAX_FILE_SIZE // (1024*1024)} MB")

    # Validar cantidad de archivos del cliente
    count_result = await db.execute(
        select(ClientFile).where(
            ClientFile.client_id == client_id,
            ClientFile.tenant_id == tenant_id
        )
    )
    existing_files = count_result.scalars().all()
    if len(existing_files) >= MAX_FILES_PER_CLIENT:
        raise HTTPException(400, f"Máximo {MAX_FILES_PER_CLIENT} archivos por cliente alcanzado")

    # Generar nombre único y guardar en disco
    unique_name = f"{category.value}_{uuid.uuid4().hex[:8]}{ext}"
    upload_dir = _get_upload_dir(tenant_id, client_id)
    file_path = upload_dir / unique_name

    with open(file_path, "wb") as f:
        f.write(content)

    # Guardar registro en BD
    db_file = ClientFile(
        tenant_id=tenant_id,
        client_id=client_id,
        file_name=file.filename,
        stored_name=unique_name,
        file_path=str(file_path),
        file_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        category=category,
        description=description,
        uploaded_by=current_user.id,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    return db_file


# ── GET: Listar archivos del cliente ──────────────────────────
@router.get("/", response_model=List[ClientFileListResponse])
async def list_client_files(
    client_id: int,
    category: Optional[FileCategory] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Listar todos los archivos de un cliente, con filtro opcional por categoría."""
    tenant_id = current_user.tenant_id

    await _get_client_or_404(client_id, tenant_id, db)

    query = select(ClientFile).where(
        ClientFile.client_id == client_id,
        ClientFile.tenant_id == tenant_id
    )

    if category:
        query = query.where(ClientFile.category == category)

    query = query.order_by(ClientFile.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


# ── GET: Descargar archivo ────────────────────────────────────
@router.get("/{file_id}")
async def download_client_file(
    client_id: int,
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Descargar un archivo específico del cliente."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(ClientFile).where(
            ClientFile.id == file_id,
            ClientFile.client_id == client_id,
            ClientFile.tenant_id == tenant_id
        )
    )
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(404, "Archivo no encontrado")

    if not os.path.exists(db_file.file_path):
        raise HTTPException(404, "Archivo no encontrado en disco")

    return FileResponse(
        path=db_file.file_path,
        filename=db_file.file_name,
        media_type=db_file.file_type,
    )


# ── DELETE: Eliminar archivo ──────────────────────────────────
@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_file(
    client_id: int,
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Eliminar un archivo del cliente (BD + disco)."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(ClientFile).where(
            ClientFile.id == file_id,
            ClientFile.client_id == client_id,
            ClientFile.tenant_id == tenant_id
        )
    )
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(404, "Archivo no encontrado")

    # Eliminar de disco (si existe)
    if os.path.exists(db_file.file_path):
        os.remove(db_file.file_path)

    # Eliminar de BD
    await db.delete(db_file)
    await db.commit()