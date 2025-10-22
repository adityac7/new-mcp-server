"""
UI Routes for MCP Analytics Server Dashboard
Serves HTMX-based web interface for dataset and query log management
"""

from fastapi import APIRouter, Request, Form, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
import os
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Dataset, QueryLog, DatasetSchema
from app.encryption import get_encryption_manager
from app.workers.tasks import process_new_dataset

# Initialize router and templates
router = APIRouter(prefix="/ui", tags=["UI"])
templates = Jinja2Templates(directory="app/ui/templates")


# =============================================================================
# Dashboard Routes
# =============================================================================

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard homepage with overview stats"""

    # Calculate stats
    total_datasets = db.query(Dataset).count()
    active_datasets = db.query(Dataset).filter(Dataset.is_active == True).count()

    # Query stats for today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    queries_today = db.query(QueryLog).filter(QueryLog.executed_at >= today_start).count()

    # Average query time
    avg_time = db.query(func.avg(QueryLog.execution_time_ms)).scalar()
    avg_time_ms = int(avg_time) if avg_time else 0

    # Recent datasets
    recent_datasets = db.query(Dataset).order_by(desc(Dataset.created_at)).limit(5).all()

    # Recent query logs
    recent_logs = db.query(QueryLog).order_by(desc(QueryLog.executed_at)).limit(5).all()

    stats = {
        'total_datasets': total_datasets,
        'active_datasets': active_datasets,
        'queries_today': queries_today,
        'avg_time_ms': avg_time_ms
    }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_datasets": recent_datasets,
        "recent_logs": recent_logs
    })


# =============================================================================
# Dataset Management Routes
# =============================================================================

@router.get("/datasets", response_class=HTMLResponse)
async def list_datasets(request: Request, db: Session = Depends(get_db)):
    """List all datasets"""

    datasets = db.query(Dataset).order_by(desc(Dataset.created_at)).all()

    # Add table count to each dataset
    for dataset in datasets:
        schema_count = db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == dataset.id
        ).count()
        dataset.table_count = schema_count

    total_datasets = len(datasets)
    active_datasets = sum(1 for d in datasets if d.is_active)
    pending_datasets = sum(1 for d in datasets if not d.is_active)

    return templates.TemplateResponse("datasets.html", {
        "request": request,
        "datasets": datasets,
        "total_datasets": total_datasets,
        "active_datasets": active_datasets,
        "pending_datasets": pending_datasets
    })


@router.get("/datasets/new", response_class=HTMLResponse)
async def new_dataset_form(request: Request):
    """Show add dataset form"""
    return templates.TemplateResponse("dataset_new.html", {
        "request": request
    })


@router.post("/datasets", response_class=HTMLResponse)
async def create_dataset(
    request: Request,
    name: str = Form(...),
    connection_string: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Create new dataset and trigger background profiling"""

    # Encrypt connection string
    encryption_manager = get_encryption_manager()
    encrypted_conn_str = encryption_manager.encrypt(connection_string)

    # Create dataset
    dataset = Dataset(
        name=name,
        description=description,
        connection_string_encrypted=encrypted_conn_str,
        is_active=False  # Will be activated after profiling
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Trigger background profiling
    process_new_dataset.delay(dataset.id)

    return RedirectResponse(url="/ui/datasets", status_code=303)


@router.get("/datasets/{dataset_id}", response_class=HTMLResponse)
async def dataset_detail(
    request: Request,
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """Show dataset details with schema and recent queries"""

    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get schema metadata
    schema_records = db.query(DatasetSchema).filter(
        DatasetSchema.dataset_id == dataset_id
    ).all()

    # Group by table
    schema = {"tables": {}}
    total_columns = 0

    for record in schema_records:
        if record.table_name not in schema["tables"]:
            schema["tables"][record.table_name] = {"columns": []}

        schema["tables"][record.table_name]["columns"].append({
            "name": record.column_name,
            "type": record.data_type,
            "nullable": record.is_nullable,
            "description": record.llm_description
        })
        total_columns += 1

    # Recent queries for this dataset
    recent_queries = db.query(QueryLog).filter(
        QueryLog.dataset_id == dataset_id
    ).order_by(desc(QueryLog.executed_at)).limit(10).all()

    # Queries today for this dataset
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    queries_today = db.query(QueryLog).filter(
        QueryLog.dataset_id == dataset_id,
        QueryLog.executed_at >= today_start
    ).count()

    return templates.TemplateResponse("dataset_detail.html", {
        "request": request,
        "dataset": dataset,
        "schema": schema,
        "total_columns": total_columns,
        "recent_queries": recent_queries,
        "queries_today": queries_today
    })


@router.post("/datasets/{dataset_id}/activate")
async def activate_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Activate a dataset"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset.is_active = True
    db.commit()

    return {"success": True, "message": "Dataset activated"}


@router.post("/datasets/{dataset_id}/deactivate")
async def deactivate_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Deactivate a dataset"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset.is_active = False
    db.commit()

    return {"success": True, "message": "Dataset deactivated"}


@router.post("/datasets/{dataset_id}/reprocess")
async def reprocess_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Trigger schema reprocessing for a dataset"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete existing schema metadata
    db.query(DatasetSchema).filter(DatasetSchema.dataset_id == dataset_id).delete()
    db.commit()

    # Trigger background profiling
    process_new_dataset.delay(dataset_id)

    return {"success": True, "message": "Reprocessing started"}


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Delete a dataset"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete schema metadata
    db.query(DatasetSchema).filter(DatasetSchema.dataset_id == dataset_id).delete()

    # Delete query logs
    db.query(QueryLog).filter(QueryLog.dataset_id == dataset_id).delete()

    # Delete dataset
    db.delete(dataset)
    db.commit()

    return {"success": True, "message": "Dataset deleted"}


# =============================================================================
# Query Log Routes
# =============================================================================

@router.get("/logs", response_class=HTMLResponse)
async def query_logs(
    request: Request,
    dataset_id: Optional[int] = Query(None),
    client_tool: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    """Query logs page with filtering and pagination"""

    # Build query
    query = db.query(QueryLog)

    # Apply filters
    if dataset_id:
        query = query.filter(QueryLog.dataset_id == dataset_id)
    if client_tool:
        query = query.filter(QueryLog.client_tool == client_tool)
    if status:
        if status == "success":
            query = query.filter(QueryLog.success == True)
        elif status == "error":
            query = query.filter(QueryLog.success == False)

    # Count total
    total_logs = query.count()

    # Pagination
    per_page = 50
    total_pages = (total_logs + per_page - 1) // per_page
    offset = (page - 1) * per_page

    logs = query.order_by(desc(QueryLog.executed_at)).limit(per_page).offset(offset).all()

    # Calculate stats
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_queries = db.query(QueryLog).count()
    success_count = db.query(QueryLog).filter(QueryLog.success == True).count()
    success_rate = int((success_count / total_queries * 100)) if total_queries > 0 else 0

    avg_time = db.query(func.avg(QueryLog.execution_time_ms)).scalar()
    avg_time_ms = int(avg_time) if avg_time else 0

    queries_today = db.query(QueryLog).filter(QueryLog.executed_at >= today_start).count()

    stats = {
        'total_queries': total_queries,
        'success_rate': success_rate,
        'avg_time_ms': avg_time_ms,
        'queries_today': queries_today
    }

    # Get all datasets for filter dropdown
    datasets = db.query(Dataset).all()

    return templates.TemplateResponse("logs.html", {
        "request": request,
        "logs": logs,
        "stats": stats,
        "datasets": datasets,
        "selected_dataset_id": dataset_id,
        "page": page,
        "total_pages": total_pages
    })


@router.delete("/logs")
async def clear_logs(db: Session = Depends(get_db)):
    """Clear all query logs"""
    db.query(QueryLog).delete()
    db.commit()

    return {"success": True, "message": "All logs cleared"}
