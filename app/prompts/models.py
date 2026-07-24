"""
Prompt Management System

This module implements prompt templates and management for AICF v2.
Supports versioning, activation, and retrieval of prompts.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.connection import Base


class PromptTemplate(Base):
    """
    Prompt template model.
    
    Stores reusable prompt templates with versioning support.
    Each agent type can have multiple versions, but only one active version.
    """
    __tablename__ = "prompt_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identification
    name = Column(String(255), nullable=False, index=True)  # Human-readable name
    slug = Column(String(100), nullable=False, index=True)  # URL-friendly identifier
    
    # Agent association
    agent_type = Column(String(100), nullable=False, index=True)  # Which agent uses this
    
    # Versioning
    version = Column(String(20), nullable=False)  # Semantic versioning (e.g., "1.0.0")
    is_active = Column(Boolean, default=False, index=True)  # Is this the current active version?
    is_major = Column(Boolean, default=False)  # Is this a major version change?
    
    # Prompt content
    system_prompt = Column(Text, nullable=False)  # The main system prompt
    user_prompt_template = Column(Text, nullable=True)  # Optional user prompt template
    
    # Variables that can be substituted
    variables = Column(JSON, default=list)  # List of variable names: ["topic", "tone", etc.]
    default_values = Column(JSON, default=dict)  # Default values for variables
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # For categorization
    prompt_metadata = Column(JSON, default=dict)  # Additional metadata (renamed from 'metadata')
    
    # Organization scoping (null = global template)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Authorship
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships (using lazy string references - deferred to avoid circular imports)
    # Note: These relationships require the Organization and User models to be defined
    # In production, these are configured after all models are loaded
    
    __table_args__ = (
        # Ensure unique version per agent type within organization scope
        UniqueConstraint('agent_type', 'version', 'organization_id', name='uq_prompt_agent_version_org'),
        # Ensure only one active version per agent type within organization scope
        Index('idx_prompt_active', 'agent_type', 'is_active', 'organization_id'),
        Index('idx_prompt_slug_org', 'slug', 'organization_id'),
    )
    
    def __repr__(self):
        return f"<PromptTemplate(id={self.id}, name='{self.name}', version='{self.version}', active={self.is_active})>"
    
    def render(self, **kwargs) -> Dict[str, str]:
        """
        Render the prompt with variable substitution.
        
        Args:
            **kwargs: Variable values to substitute
            
        Returns:
            Dictionary with 'system' and optionally 'user' rendered prompts
        """
        result = {"system": self.system_prompt}
        
        # Merge default values with provided values
        variables = {**(self.default_values or {}), **kwargs}
        
        # Substitute in system prompt
        system_prompt = self.system_prompt
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"  # {{variable}}
            system_prompt = system_prompt.replace(placeholder, str(var_value))
        result["system"] = system_prompt
        
        # Substitute in user prompt if present
        if self.user_prompt_template:
            user_prompt = self.user_prompt_template
            for var_name, var_value in variables.items():
                placeholder = f"{{{{{var_name}}}}}"
                user_prompt = user_prompt.replace(placeholder, str(var_value))
            result["user"] = user_prompt
        
        return result


class PromptVersionHistory(Base):
    """
    Prompt version history tracking.
    
    Records all changes to prompt templates for audit and rollback.
    """
    __tablename__ = "prompt_version_history"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_template_id = Column(Integer, ForeignKey("prompt_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Version info
    version = Column(String(20), nullable=False)
    change_type = Column(String(50), nullable=False)  # created, updated, activated, deactivated
    
    # Content snapshot
    system_prompt_snapshot = Column(Text, nullable=False)
    variables_snapshot = Column(JSON, nullable=True)
    
    # Change metadata
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    change_reason = Column(Text, nullable=True)
    diff_summary = Column(Text, nullable=True)  # Brief description of changes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships (deferred to avoid circular imports)
    # Note: These relationships require the PromptTemplate and User models to be defined
    # In production, these are configured after all models are loaded
    
    __table_args__ = (
        Index('idx_prompt_hist_template', 'prompt_template_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<PromptVersionHistory(id={self.id}, template={self.prompt_template_id}, version='{self.version}')>"


class PromptService:
    """
    Service layer for prompt template management.
    
    Provides CRUD operations, versioning, and activation logic.
    """
    
    def __init__(self, db: Session, organization_id: Optional[int] = None):
        self.db = db
        self.organization_id = organization_id
    
    def create_template(
        self,
        name: str,
        slug: str,
        agent_type: str,
        system_prompt: str,
        version: str = "1.0.0",
        user_prompt_template: Optional[str] = None,
        variables: Optional[List[str]] = None,
        default_values: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        set_active: bool = True,
    ) -> PromptTemplate:
        """
        Create a new prompt template.
        
        Args:
            name: Human-readable name
            slug: URL-friendly identifier
            agent_type: Type of agent that uses this prompt
            system_prompt: The main system prompt text
            version: Semantic version string
            user_prompt_template: Optional user prompt template
            variables: List of variable names
            default_values: Default values for variables
            description: Template description
            tags: Categorization tags
            set_active: Whether to activate this template immediately
            
        Returns:
            Created PromptTemplate instance
        """
        # Check for existing active version
        if set_active:
            self._deactivate_all(agent_type)
        
        template = PromptTemplate(
            name=name,
            slug=slug,
            agent_type=agent_type,
            version=version,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            variables=variables or [],
            default_values=default_values or {},
            description=description,
            tags=tags or [],
            organization_id=self.organization_id,
            is_active=set_active,
            activated_at=datetime.utcnow() if set_active else None,
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        # Record version history
        self._record_history(template, "created")
        
        return template
    
    def get_template(self, template_id: int) -> Optional[PromptTemplate]:
        """Get a template by ID."""
        query = self.db.query(PromptTemplate).filter(PromptTemplate.id == template_id)
        if self.organization_id:
            query = query.filter(
                (PromptTemplate.organization_id == self.organization_id) | 
                (PromptTemplate.organization_id.is_(None))
            )
        return query.first()
    
    def get_by_slug(self, slug: str) -> Optional[PromptTemplate]:
        """Get a template by slug."""
        query = self.db.query(PromptTemplate).filter(PromptTemplate.slug == slug)
        if self.organization_id:
            query = query.filter(
                (PromptTemplate.organization_id == self.organization_id) | 
                (PromptTemplate.organization_id.is_(None))
            )
        return query.first()
    
    def get_active_template(self, agent_type: str) -> Optional[PromptTemplate]:
        """
        Get the active template for an agent type.
        
        Args:
            agent_type: The agent type to get template for
            
        Returns:
            Active PromptTemplate or None
        """
        query = self.db.query(PromptTemplate).filter(
            PromptTemplate.agent_type == agent_type,
            PromptTemplate.is_active == True
        )
        
        if self.organization_id:
            # Prefer organization-specific templates
            org_template = query.filter(
                PromptTemplate.organization_id == self.organization_id
            ).first()
            if org_template:
                return org_template
            
            # Fall back to global templates
            query = query.filter(PromptTemplate.organization_id.is_(None))
        
        return query.first()
    
    def get_all_versions(self, agent_type: str) -> List[PromptTemplate]:
        """Get all versions of templates for an agent type."""
        query = self.db.query(PromptTemplate).filter(
            PromptTemplate.agent_type == agent_type
        )
        
        if self.organization_id:
            query = query.filter(
                (PromptTemplate.organization_id == self.organization_id) | 
                (PromptTemplate.organization_id.is_(None))
            )
        
        return query.order_by(PromptTemplate.created_at.desc()).all()
    
    def activate_template(self, template_id: int) -> Optional[PromptTemplate]:
        """
        Activate a specific template version.
        
        Deactivates all other versions of the same agent type.
        
        Args:
            template_id: ID of template to activate
            
        Returns:
            Activated template or None
        """
        template = self.get_template(template_id)
        if not template:
            return None
        
        # Deactivate all others
        self._deactivate_all(template.agent_type)
        
        # Activate this one
        template.is_active = True
        template.activated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(template)
        
        # Record history
        self._record_history(template, "activated")
        
        return template
    
    def deactivate_template(self, template_id: int) -> bool:
        """Deactivate a template."""
        template = self.get_template(template_id)
        if not template or not template.is_active:
            return False
        
        template.is_active = False
        template.activated_at = None
        self.db.commit()
        
        self._record_history(template, "deactivated")
        return True
    
    def update_template(
        self,
        template_id: int,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
        variables: Optional[List[str]] = None,
        default_values: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        bump_version: bool = True,
    ) -> Optional[PromptTemplate]:
        """
        Update a template, optionally bumping version.
        
        Args:
            template_id: Template to update
            system_prompt: New system prompt
            user_prompt_template: New user prompt template
            variables: New variables list
            default_values: New default values
            description: New description
            tags: New tags
            bump_version: Whether to create new version
            
        Returns:
            Updated template or None
        """
        template = self.get_template(template_id)
        if not template:
            return None
        
        was_active = template.is_active
        
        if bump_version:
            # Parse and increment version
            parts = template.version.split('.')
            try:
                parts[-1] = str(int(parts[-1]) + 1)
            except (ValueError, IndexError):
                parts.append('1')
            template.version = '.'.join(parts)
        
        if system_prompt is not None:
            template.system_prompt = system_prompt
        if user_prompt_template is not None:
            template.user_prompt_template = user_prompt_template
        if variables is not None:
            template.variables = variables
        if default_values is not None:
            template.default_values = default_values
        if description is not None:
            template.description = description
        if tags is not None:
            template.tags = tags
        
        template.updated_at = datetime.utcnow()
        
        # If was active, keep it active
        if was_active:
            template.activated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(template)
        
        # Record history
        self._record_history(template, "updated")
        
        return template
    
    def delete_template(self, template_id: int) -> bool:
        """Delete a template (only if not active)."""
        template = self.get_template(template_id)
        if not template:
            return False
        
        if template.is_active:
            raise ValueError("Cannot delete active template. Deactivate first.")
        
        self.db.delete(template)
        self.db.commit()
        return True
    
    def list_templates(
        self,
        agent_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PromptTemplate]:
        """List templates with optional filtering."""
        query = self.db.query(PromptTemplate)
        
        if self.organization_id:
            query = query.filter(
                (PromptTemplate.organization_id == self.organization_id) | 
                (PromptTemplate.organization_id.is_(None))
            )
        
        if agent_type:
            query = query.filter(PromptTemplate.agent_type == agent_type)
        
        return query.order_by(
            PromptTemplate.agent_type,
            PromptTemplate.created_at.desc()
        ).offset(offset).limit(limit).all()
    
    def _deactivate_all(self, agent_type: str) -> None:
        """Deactivate all templates for an agent type."""
        query = self.db.query(PromptTemplate).filter(
            PromptTemplate.agent_type == agent_type,
            PromptTemplate.is_active == True
        )
        if self.organization_id:
            query = query.filter(PromptTemplate.organization_id == self.organization_id)
        
        for template in query.all():
            template.is_active = False
            template.activated_at = None
        
        self.db.commit()
    
    def _record_history(
        self,
        template: PromptTemplate,
        change_type: str,
        changed_by: Optional[int] = None,
        change_reason: Optional[str] = None,
    ) -> None:
        """Record a version history entry."""
        history = PromptVersionHistory(
            prompt_template_id=template.id,
            version=template.version,
            change_type=change_type,
            system_prompt_snapshot=template.system_prompt,
            variables_snapshot=template.variables,
            changed_by=changed_by,
            change_reason=change_reason,
        )
        self.db.add(history)
        self.db.commit()
    
    def get_version_history(self, template_id: int) -> List[PromptVersionHistory]:
        """Get version history for a template."""
        return self.db.query(PromptVersionHistory).filter(
            PromptVersionHistory.prompt_template_id == template_id
        ).order_by(PromptVersionHistory.created_at.desc()).all()
