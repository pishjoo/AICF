"""
API Routes

FastAPI routes for profiles, projects, and workflow management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database.connection import get_db
# Temporarily disabled legacy imports for v2 compatibility
# from database.models import ContentProfile, Project, WorkflowStage, WorkflowStatus as DBWorkflowStatus
from database.models import ChannelProfile as ContentProfile, Episode as Project, AgentExecution as WorkflowStage
from enum import Enum
class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

from app.api.schemas import (
    ContentProfileCreate,
    ContentProfileUpdate,
    ContentProfileResponse,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    WorkflowStatusResponse,
    WorkflowStageResponse,
    MessageResponse,
    AgentExecuteRequest,
    AgentExecuteResponse
)
from app.auth.routes import router as auth_router
from app.api.health import router as health_router


router = APIRouter()

# Include authentication routes
router.include_router(auth_router)

# Include health check routes
router.include_router(health_router)


# ============== Content Profile Endpoints ==============

@router.get("/profiles", response_model=List[ContentProfileResponse], tags=["Profiles"])
def list_profiles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all content profiles."""
    profiles = db.query(ContentProfile).filter(ContentProfile.is_active == True).offset(skip).limit(limit).all()
    return profiles


@router.post("/profiles", response_model=ContentProfileResponse, status_code=status.HTTP_201_CREATED, tags=["Profiles"])
def create_profile(profile: ContentProfileCreate, db: Session = Depends(get_db)):
    """Create a new content profile."""
    db_profile = ContentProfile(**profile.model_dump())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@router.get("/profiles/{profile_id}", response_model=ContentProfileResponse, tags=["Profiles"])
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    """Get a specific content profile by ID."""
    profile = db.query(ContentProfile).filter(ContentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/profiles/{profile_id}", response_model=ContentProfileResponse, tags=["Profiles"])
def update_profile(profile_id: int, profile_update: ContentProfileUpdate, db: Session = Depends(get_db)):
    """Update a content profile."""
    profile = db.query(ContentProfile).filter(ContentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/profiles/{profile_id}", response_model=MessageResponse, tags=["Profiles"])
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    """Delete (deactivate) a content profile."""
    profile = db.query(ContentProfile).filter(ContentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile.is_active = False
    db.commit()
    
    return MessageResponse(message=f"Profile '{profile.name}' has been deactivated")


# ============== Project Endpoints ==============

@router.get("/projects", response_model=List[ProjectResponse], tags=["Projects"])
def list_projects(skip: int = 0, limit: int = 100, profile_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all projects, optionally filtered by profile."""
    query = db.query(Project)
    if profile_id:
        query = query.filter(Project.profile_id == profile_id)
    projects = query.offset(skip).limit(limit).all()
    return projects


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, tags=["Projects"])
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    # Verify profile exists
    profile = db.query(ContentProfile).filter(ContentProfile.id == project.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Content profile not found")
    
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a specific project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
def update_project(project_id: int, project_update: ProjectUpdate, db: Session = Depends(get_db)):
    """Update a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}", response_model=MessageResponse, tags=["Projects"])
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    
    return MessageResponse(message=f"Project '{project.title}' has been deleted")


# ============== Workflow Endpoints ==============

@router.get("/projects/{project_id}/workflow", response_model=WorkflowStatusResponse, tags=["Workflow"])
def get_workflow_status(project_id: int, db: Session = Depends(get_db)):
    """Get the workflow status for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    stages = db.query(WorkflowStage).filter(
        WorkflowStage.project_id == project_id
    ).order_by(WorkflowStage.stage_order).all()
    
    stage_responses = [
        WorkflowStageResponse(
            id=stage.id,
            project_id=stage.project_id,
            stage_type=stage.stage_type,
            stage_order=stage.stage_order,
            status=stage.status,
            agent_name=stage.agent_name,
            started_at=stage.started_at,
            completed_at=stage.completed_at,
            duration_seconds=stage.duration_seconds,
            error_message=stage.error_message
        )
        for stage in stages
    ]
    
    return WorkflowStatusResponse(
        project_id=project.id,
        project_title=project.title,
        overall_status=project.status,
        current_stage=project.current_stage,
        stages=stage_responses
    )


@router.post("/projects/{project_id}/workflow/execute", response_model=AgentExecuteResponse, tags=["Workflow"])
def execute_workflow_stage(
    project_id: int,
    request: AgentExecuteRequest,
    stage: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Execute a workflow stage or the full workflow.
    
    If stage parameter is provided, executes only that stage.
    Otherwise, executes from current stage to completion.
    """
    from core.workflow import WorkflowEngine
    from database.models import WorkflowStageType
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Initialize workflow engine
    engine = WorkflowEngine(db)
    
    # TODO: Register agents here once implemented
    # For now, return a placeholder response
    return AgentExecuteResponse(
        success=False,
        output={"message": "Workflow execution not yet implemented - agents pending"},
        error_message="Agents not yet registered"
    )

