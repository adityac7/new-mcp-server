"""
MCP Analytics Server - Phase 2 Main Application
Multi-dataset support with LLM-powered metadata
"""
import os
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, init_database, test_connection
from app.models import Dataset, DatasetSchema, Metadata, QueryLog
from app.encryption import get_encryption_manager, generate_encryption_key
from app.workers.tasks import process_new_dataset

# Initialize FastAPI app
app = FastAPI(
    title="MCP Analytics Server",
    description="Multi-dataset analytics platform with AI-powered metadata",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    init_database()
    print("✅ Database initialized")


# Pydantic models for API
class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    connection_string: str


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SchemaResponse(BaseModel):
    id: int
    table_name: str
    column_name: str
    data_type: str
    is_nullable: bool
    
    class Config:
        from_attributes = True


class MetadataResponse(BaseModel):
    id: int
    table_name: str
    column_name: str
    description: Optional[str]
    generated_at: datetime
    model_used: str
    
    class Config:
        from_attributes = True


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "phase": "Phase 2 - Multi-dataset + LLM Metadata"
    }


# Dataset management endpoints
@app.post("/api/datasets", response_model=DatasetResponse)
async def create_dataset(
    dataset: DatasetCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new dataset and trigger background processing
    
    This will:
    1. Test the connection
    2. Encrypt and store the connection string
    3. Trigger background schema profiling and metadata generation
    """
    # Check if dataset name already exists
    existing = db.query(Dataset).filter(Dataset.name == dataset.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Dataset name already exists")
    
    # Test connection
    is_valid, message = test_connection(dataset.connection_string)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Connection failed: {message}")
    
    # Encrypt connection string
    encryption_manager = get_encryption_manager()
    encrypted_connection = encryption_manager.encrypt(dataset.connection_string)
    
    # Create dataset
    db_dataset = Dataset(
        name=dataset.name,
        description=dataset.description,
        connection_string_encrypted=encrypted_connection,
        is_active=True
    )
    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)
    
    # Trigger background processing
    background_tasks.add_task(process_new_dataset, db_dataset.id)
    
    return db_dataset


@app.get("/api/datasets", response_model=List[DatasetResponse])
async def list_datasets(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all datasets"""
    query = db.query(Dataset)
    if active_only:
        query = query.filter(Dataset.is_active == True)
    
    datasets = query.order_by(Dataset.created_at.desc()).all()
    return datasets


@app.get("/api/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Get a specific dataset by ID"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@app.delete("/api/datasets/{dataset_id}")
async def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Delete a dataset (soft delete by marking inactive)"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    dataset.is_active = False
    db.commit()
    
    return {"message": "Dataset deactivated successfully"}


# Schema endpoints
@app.get("/api/datasets/{dataset_id}/schema", response_model=List[SchemaResponse])
async def get_dataset_schema(dataset_id: int, db: Session = Depends(get_db)):
    """Get schema information for a dataset"""
    # Check if dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Get schema
    schemas = db.query(DatasetSchema).filter(
        DatasetSchema.dataset_id == dataset_id
    ).order_by(DatasetSchema.table_name, DatasetSchema.column_name).all()
    
    return schemas


# Metadata endpoints
@app.get("/api/datasets/{dataset_id}/metadata", response_model=List[MetadataResponse])
async def get_dataset_metadata(
    dataset_id: int,
    table_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get AI-generated metadata for a dataset"""
    # Check if dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Get metadata
    query = db.query(Metadata).filter(Metadata.dataset_id == dataset_id)
    
    if table_name:
        query = query.filter(Metadata.table_name == table_name)
    
    metadata = query.order_by(Metadata.table_name, Metadata.column_name).all()
    
    return metadata


# Processing status endpoint
@app.get("/api/datasets/{dataset_id}/status")
async def get_dataset_status(dataset_id: int, db: Session = Depends(get_db)):
    """Get processing status for a dataset"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Count schemas and metadata
    schema_count = db.query(DatasetSchema).filter(
        DatasetSchema.dataset_id == dataset_id
    ).count()
    
    metadata_count = db.query(Metadata).filter(
        Metadata.dataset_id == dataset_id
    ).count()
    
    # Get unique tables
    tables = db.query(DatasetSchema.table_name).filter(
        DatasetSchema.dataset_id == dataset_id
    ).distinct().all()
    
    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset.name,
        "is_active": dataset.is_active,
        "tables_found": len(tables),
        "columns_profiled": schema_count,
        "metadata_generated": metadata_count,
        "processing_complete": schema_count > 0 and metadata_count > 0
    }


# Trigger manual reprocessing
@app.post("/api/datasets/{dataset_id}/reprocess")
async def reprocess_dataset(
    dataset_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger reprocessing of a dataset"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Trigger background processing
    background_tasks.add_task(process_new_dataset, dataset_id)
    
    return {"message": "Reprocessing triggered", "dataset_id": dataset_id}


# Utility endpoint to generate encryption key
@app.get("/api/utils/generate-key")
async def generate_key():
    """Generate a new encryption key (for setup only)"""
    return {
        "encryption_key": generate_encryption_key(),
        "note": "Store this securely in your ENCRYPTION_KEY environment variable"
    }


# MCP endpoint placeholder - will be handled by separate MCP server
@app.api_route("/mcp", methods=["GET", "POST", "DELETE"])
async def mcp_endpoint_placeholder(request: Request):
    """
    MCP protocol endpoint
    Note: In production, run the MCP server separately using server.py
    """
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": -32000,
            "message": "MCP endpoint available. For full MCP support, run server.py on a separate port."
        },
        "id": None
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "MCP Analytics Server",
        "version": "2.0.0",
        "phase": "Phase 2 - Multi-dataset + LLM Metadata",
        "features": [
            "Multi-dataset management",
            "Encrypted connection strings",
            "AI-powered metadata generation",
            "Background processing with Celery",
            "MCP protocol support"
        ],
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "datasets": "/api/datasets",
            "mcp": "/mcp (run server.py for full MCP support)"
        }
    }

