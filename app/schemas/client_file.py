"""
Sistema ISP - Schemas: Archivos de Cliente
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.client_file import FileCategory


class ClientFileUpload(BaseModel):
    """Schema para el form-data (solo los campos extras, el archivo va aparte)"""
    category: FileCategory = FileCategory.OTRO
    description: Optional[str] = Field(None, max_length=255)


class ClientFileResponse(BaseModel):
    id: int
    client_id: int
    file_name: str
    file_type: str
    file_size: int
    category: FileCategory
    description: Optional[str]
    uploaded_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ClientFileListResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    file_size: int
    category: FileCategory
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True