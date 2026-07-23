"""
AICF v2 Database Models

Complete SQLAlchemy ORM models for AICF v2 multi-tenant SaaS architecture.

Domain Model:
- Identity & SaaS: Organization, Team, User, Role, Permission, UserRole, TeamMember
- Channel System: ChannelProfile, ContentStrategy
- Content Planning: Playlist, Episode
- Production: ProductionTemplate, ContentJob
- Media: Asset
- AI Operations: AgentExecution
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum,
    JSON, Boolean, Float, BigInteger, UniqueConstraint, Index, ForeignKeyConstraint
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid

from database.connection import Base


# =============================================================================
# ENUMS
# =============================================================================

class PlaylistType(str, enum.Enum):
    """Playlist type enumeration."""
    PLANNED_PLAYLIST = "planned_playlist"  # Pre-defined content calendar
    DYNAMIC_PLAYLIST = "dynamic_playlist"  # AI-generated from sources


class EpisodeStatus(str, enum.Enum):
    """Episode lifecycle status enumeration."""
    PLANNED = "planned"
    RESEARCHING = "researching"
    SCRIPT_READY = "script_ready"
    PRODUCING = "producing"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentJobStatus(str, enum.Enum):
    """Content job execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class AgentExecutionStatus(str, enum.Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AssetType(str, enum.Enum):
    """Asset type enumeration."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    SCRIPT = "script"
    THUMBNAIL = "thumbnail"
    DOCUMENT = "document"
    OTHER = "other"


class RoleType(str, enum.Enum):
    """Built-in role types."""
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


# =============================================================================
# MIXINS
# =============================================================================

class TenantMixin:
    """Mixin for tenant-owned entities with organization isolation."""
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)
    
    # Add index for tenant isolation queries
    __table_args__ = (
        Index('idx_tenant_entity', 'organization_id', 'id'),
    )


class TimestampMixin:
    """Mixin for entities with timestamps only."""
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)


# =============================================================================
# IDENTITY & SAAS MODELS
# =============================================================================

class Organization(Base):
    """
    Organization model - Top-level tenant in multi-tenant architecture.
    
    Represents a company or business entity that owns teams, users, and all content.
    Provides complete data isolation between different organizations.
    """
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text, nullable=True)
    
    # Billing & Subscription
    subscription_plan = Column(String(50), default="free")  # free, pro, enterprise
    subscription_status = Column(String(50), default="active")
    stripe_customer_id = Column(String(255), nullable=True)
    
    # Limits & Quotas
    max_teams = Column(Integer, default=5)
    max_users = Column(Integer, default=10)
    max_channels = Column(Integer, default=10)
    storage_limit_gb = Column(Float, default=10.0)
    
    # Settings
    settings = Column(JSON, default=dict)
    extra_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan")
    channel_profiles = relationship("ChannelProfile", back_populates="organization", cascade="all, delete-orphan")
    
    # Audit logs
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_org_slug', 'slug', unique=True),
        Index('idx_org_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Team(TenantMixin, Base):
    """
    Team model - Subdivision within an organization.
    
    Teams allow organizing users into groups with specific projects or channels.
    Each team belongs to exactly one organization.
    """
    __tablename__ = "teams"
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Team settings
    settings = Column(JSON, default=dict)
    
    # Unique constraint: slug must be unique within organization
    __table_args__ = (
        UniqueConstraint('organization_id', 'slug', name='uq_team_org_slug'),
        Index('idx_team_org', 'organization_id'),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    channel_profiles = relationship("ChannelProfile", back_populates="team", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}', organization_id={self.organization_id})>"


class User(TenantMixin, Base):
    """
    User model - Individual user account within an organization.
    
    Users can belong to multiple teams and have different roles in each.
    Authentication is handled externally (JWT/OAuth2).
    """
    __tablename__ = "users"
    
    # Authentication
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Null for OAuth users
    external_auth_id = Column(String(255), nullable=True, index=True)  # Auth0, Cognito, etc.
    
    # Profile
    full_name = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Settings
    settings = Column(JSON, default=dict)
    extra_data = Column(JSON, default=dict)
    
    # Unique constraint: email must be unique within organization
    __table_args__ = (
        UniqueConstraint('organization_id', 'email', name='uq_user_org_email'),
        Index('idx_user_org', 'organization_id'),
        Index('idx_user_email', 'email'),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    team_memberships = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan", foreign_keys="TeamMember.user_id")
    role_assignments = relationship("UserRole", back_populates="user", cascade="all, delete-orphan", foreign_keys="UserRole.user_id")
    
    # Content ownership - use creator relationship name
    created_playlists = relationship("Playlist", back_populates="creator", foreign_keys="Playlist.creator_id")
    created_episodes = relationship("Episode", back_populates="creator", foreign_keys="Episode.creator_id")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', organization_id={self.organization_id})>"


class Role(TenantMixin, Base):
    """
    Role model - Custom roles within an organization.
    
    Roles define a set of permissions that can be assigned to users.
    Built-in roles: owner, admin, manager, member, viewer.
    """
    __tablename__ = "roles"
    
    name = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    # Built-in flag (cannot be deleted)
    is_builtin = Column(Boolean, default=False)
    
    # Permissions stored as JSON array of permission slugs
    permissions = Column(JSON, default=list)
    
    # Unique constraint: slug must be unique within organization
    __table_args__ = (
        UniqueConstraint('organization_id', 'slug', name='uq_role_org_slug'),
        Index('idx_role_org', 'organization_id'),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="roles")
    user_assignments = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Permission(Base):
    """
    Permission model - Granular action permissions.
    
    Permissions define specific actions that can be performed on resources.
    Format: resource:action (e.g., "channel:create", "episode:publish")
    """
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    resource = Column(String(50), nullable=False)  # e.g., "channel", "episode"
    action = Column(String(50), nullable=False)  # e.g., "create", "read", "update", "delete"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships (removed incorrect back_populates)
    # roles = relationship("Role", secondary="role_permissions", back_populates="permissions_list")
    
    def __repr__(self):
        return f"<Permission(id={self.id}, slug='{self.slug}')>"


class RolePermission(Base):
    """Association table for Role-Permission many-to-many relationship."""
    __tablename__ = "role_permissions"
    
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    
    __table_args__ = (
        Index('idx_role_permission', 'role_id', 'permission_id'),
    )


class UserRole(TenantMixin, Base):
    """
    UserRole model - Assignment of roles to users.
    
    Links users to roles within an organization context.
    A user can have multiple roles.
    """
    __tablename__ = "user_roles"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Optional: override permissions for this specific assignment
    custom_permissions = Column(JSON, nullable=True)
    
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', 'role_id', name='uq_user_role_org'),
        Index('idx_user_role_user', 'user_id'),
        Index('idx_user_role_role', 'role_id'),
    )
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User", back_populates="role_assignments", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_assignments")
    granted_by_user = relationship("User", foreign_keys=[granted_by])
    
    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class TeamMember(TenantMixin, Base):
    """
    TeamMember model - Membership of users in teams.
    
    Links users to teams with optional role overrides.
    """
    __tablename__ = "team_members"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Optional: team-specific role (overrides org role for team context)
    role_override = Column(String(50), nullable=True)
    
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    __table_args__ = (
        UniqueConstraint('team_id', 'user_id', name='uq_team_member'),
        Index('idx_team_member_team', 'team_id'),
        Index('idx_team_member_user', 'user_id'),
    )
    
    # Relationships
    organization = relationship("Organization")
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships", foreign_keys=[user_id])
    invited_by_user = relationship("User", foreign_keys=[invited_by])
    
    def __repr__(self):
        return f"<TeamMember(team_id={self.team_id}, user_id={self.user_id})>"


class AuditLog(TenantMixin, Base):
    """
    AuditLog model - Security and compliance logging.
    
    Records all significant actions for security, compliance, and debugging.
    """
    __tablename__ = "audit_logs"
    
    # Action details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=True)
    
    # Actor
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    
    # Data
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    changes = Column(JSON, nullable=True)  # Before/after values
    
    # Result
    status = Column(String(20), nullable=True)  # success, failure
    error_message = Column(Text, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", foreign_keys=[user_id])
    
    __table_args__ = (
        Index('idx_audit_action', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', resource='{self.resource_type}')>"


# =============================================================================
# CHANNEL SYSTEM MODELS
# =============================================================================

class ChannelProfile(TenantMixin, Base):
    """
    ChannelProfile model - Content identity definition.
    
    Represents a complete content channel identity across platforms.
    Contains all branding, audience, and style rules for AI agents.
    """
    __tablename__ = "channel_profiles"
    
    # Basic Identity
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    platform = Column(String(50), nullable=False)  # youtube, instagram, tiktok, linkedin, etc.
    
    # Foreign keys
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Audience Definition
    audience_definition = Column(Text, nullable=True)
    age_range_min = Column(Integer, nullable=True)
    age_range_max = Column(Integer, nullable=True)
    gender_focus = Column(String(50), nullable=True)  # male, female, all, non-binary
    interests = Column(JSON, default=list)  # List of interest keywords
    
    # Content Style
    content_style = Column(String(255), nullable=True)  # educational, entertainment, documentary, etc.
    tone = Column(String(255), nullable=True)  # professional, casual, humorous, serious
    language = Column(String(50), default="English")
    
    # Visual Identity
    visual_identity = Column(JSON, nullable=True)  # colors, fonts, logo references
    image_dimensions = Column(String(20), nullable=True)  # e.g., "1920x1080", "1080x1920"
    video_format = Column(String(20), nullable=True)  # mp4, mov, etc.
    aspect_ratio = Column(String(20), default="16:9")
    
    # Audio/Voice
    voice_type = Column(String(100), nullable=True)  # male, female, neutral, specific voice ID
    character_avatar = Column(JSON, nullable=True)  # Character descriptions for generation
    
    # Branding Rules
    branding_rules = Column(JSON, nullable=True)  # Logo usage, color restrictions, etc.
    forbidden_elements = Column(JSON, default=list)  # Elements to avoid
    recurring_characters = Column(JSON, default=list)
    
    # Content Strategy
    hashtag_strategy = Column(JSON, default=list)  # Default hashtags, strategy rules
    seo_rules = Column(JSON, nullable=True)  # SEO guidelines, keyword targets
    
    # Storytelling
    storytelling_rules = Column(Text, nullable=True)
    music_style = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    organization = relationship("Organization", back_populates="channel_profiles")
    team = relationship("Team", back_populates="channel_profiles")
    content_strategy = relationship("ContentStrategy", back_populates="channel_profile", uselist=False, cascade="all, delete-orphan")
    playlists = relationship("Playlist", back_populates="channel_profile", cascade="all, delete-orphan")
    production_templates = relationship("ProductionTemplate", back_populates="channel_profile", cascade="all, delete-orphan")
    episodes = relationship("Episode", back_populates="channel_profile", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_channel_org', 'organization_id'),
        Index('idx_channel_platform', 'platform'),
    )
    
    def __repr__(self):
        return f"<ChannelProfile(id={self.id}, name='{self.name}', platform='{self.platform}')>"


class ContentStrategy(TenantMixin, Base):
    """
    ContentStrategy model - Long-term content planning.
    
    Defines strategic goals, content pillars, and publishing schedules
    for a ChannelProfile.
    """
    __tablename__ = "content_strategies"
    
    # Foreign key
    channel_profile_id = Column(Integer, ForeignKey("channel_profiles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Strategic Goals
    goals = Column(JSON, nullable=True)  # List of goal objects {type, target, deadline}
    content_pillars = Column(JSON, default=list)  # Core content themes/topics
    
    # Publishing Schedule
    publishing_schedule = Column(JSON, nullable=True)  # {days_of_week, times, frequency}
    posting_frequency = Column(String(50), nullable=True)  # daily, weekly, bi-weekly, monthly
    target_posts_per_month = Column(Integer, nullable=True)
    
    # Platform Strategy
    platforms = Column(JSON, default=list)  # Target platforms for distribution
    cross_platform_strategy = Column(Text, nullable=True)
    
    # KPIs
    kpis = Column(JSON, nullable=True)  # Key performance indicators
    target_metrics = Column(JSON, nullable=True)  # Views, engagement, subscribers targets
    
    # Content Calendar
    content_calendar = Column(JSON, nullable=True)  # High-level calendar structure
    
    # Seasonal Campaigns
    seasonal_campaigns = Column(JSON, default=list)
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    channel_profile = relationship("ChannelProfile", back_populates="content_strategy")
    
    __table_args__ = (
        Index('idx_strategy_channel', 'channel_profile_id'),
    )
    
    def __repr__(self):
        return f"<ContentStrategy(channel_profile_id={self.channel_profile_id})>"


# =============================================================================
# CONTENT PLANNING MODELS
# =============================================================================

class Playlist(TenantMixin, Base):
    """
    Playlist model - Content collection and planning.
    
    Playlists organize episodes into thematic collections.
    Supports two types:
    - PLANNED_PLAYLIST: Pre-defined content calendar with fixed episodes
    - DYNAMIC_PLAYLIST: AI-curated from ongoing sources (RSS, news, trends)
    """
    __tablename__ = "playlists"
    
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Type
    playlist_type = Column(SQLEnum(PlaylistType), nullable=False, index=True)
    
    # Foreign keys
    channel_profile_id = Column(Integer, ForeignKey("channel_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # For dynamic playlists
    source_urls = Column(JSON, default=list)  # RSS feeds, websites to monitor
    monitoring_keywords = Column(JSON, default=list)  # Keywords for topic discovery
    auto_generate = Column(Boolean, default=False)
    
    # Episode roadmap (for planned playlists)
    episode_roadmap = Column(JSON, nullable=True)  # Pre-defined episode topics
    total_planned_episodes = Column(Integer, nullable=True)
    
    # Production settings
    production_template_id = Column(Integer, ForeignKey("production_templates.id", ondelete="SET NULL"), nullable=True)
    default_character = Column(String(255), nullable=True)
    default_style = Column(String(255), nullable=True)
    default_duration = Column(String(50), nullable=True)
    default_format = Column(String(50), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    organization = relationship("Organization")
    channel_profile = relationship("ChannelProfile", back_populates="playlists")
    creator = relationship("User", back_populates="created_playlists", foreign_keys=[creator_id])
    production_template = relationship("ProductionTemplate")
    episodes = relationship("Episode", back_populates="playlist", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_playlist_channel', 'channel_profile_id'),
        Index('idx_playlist_type', 'playlist_type'),
    )
    
    def __repr__(self):
        return f"<Playlist(id={self.id}, title='{self.title}', type='{self.playlist_type}')>"


class Episode(TenantMixin, Base):
    """
    Episode model - Single content unit.
    
    Represents one piece of content (video, post, article) through its
    entire lifecycle from planning to publication.
    """
    __tablename__ = "episodes"
    
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Lifecycle status
    status = Column(SQLEnum(EpisodeStatus), default=EpisodeStatus.PLANNED, index=True)
    
    # Foreign keys
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_profile_id = Column(Integer, ForeignKey("channel_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    production_template_id = Column(Integer, ForeignKey("production_templates.id", ondelete="SET NULL"), nullable=True)
    
    # Content data
    topic = Column(Text, nullable=True)
    research_data = Column(JSON, default=dict)
    script = Column(Text, nullable=True)
    storyboard = Column(JSON, default=list)
    
    # Production data
    assets = Column(JSON, default=list)  # References to Asset records
    thumbnail_id = Column(Integer, nullable=True)
    
    # SEO & Publishing
    seo_data = Column(JSON, default=dict)  # title, description, tags, keywords
    publish_metadata = Column(JSON, nullable=True)  # platform-specific publish data
    published_url = Column(String(500), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Scheduling
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    
    # Approval workflow
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Version tracking
    version = Column(Integer, default=1)
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    organization = relationship("Organization")
    playlist = relationship("Playlist", back_populates="episodes")
    channel_profile = relationship("ChannelProfile", back_populates="episodes")
    creator = relationship("User", back_populates="created_episodes", foreign_keys=[creator_id])
    production_template = relationship("ProductionTemplate", back_populates="episodes")
    content_jobs = relationship("ContentJob", back_populates="episode", cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="episode", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="episode", cascade="all, delete-orphan")
    quality_scores = relationship("MediaQualityScore", back_populates="episode")
    approval_requests = relationship("ApprovalRequest", back_populates="episode")
    
    __table_args__ = (
        Index('idx_episode_status', 'status'),
        Index('idx_episode_playlist', 'playlist_id'),
        Index('idx_episode_scheduled', 'scheduled_for'),
    )
    
    def __repr__(self):
        return f"<Episode(id={self.id}, title='{self.title}', status='{self.status}')>"


# =============================================================================
# PRODUCTION MODELS
# =============================================================================

class ProductionTemplate(TenantMixin, Base):
    """
    ProductionTemplate model - Reusable production rules.
    
    Defines consistent production settings for episodes including
    characters, voices, visual styles, and technical specifications.
    """
    __tablename__ = "production_templates"
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Foreign keys
    channel_profile_id = Column(Integer, ForeignKey("channel_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Character & Voice
    narrator_character = Column(JSON, nullable=True)  # Character description
    voice_id = Column(String(100), nullable=True)  # AI voice provider ID
    voice_settings = Column(JSON, nullable=True)  # Speed, pitch, emotion
    
    # Visual Style
    visual_style = Column(String(255), nullable=True)
    visual_style_prompt = Column(Text, nullable=True)  # Detailed prompt for image generation
    color_palette = Column(JSON, nullable=True)
    
    # Structure
    intro_template = Column(Text, nullable=True)  # Standard intro script/visual
    outro_template = Column(Text, nullable=True)
    segment_structure = Column(JSON, nullable=True)  # Defined segments [intro, main, conclusion]
    
    # Technical Specs
    duration_target = Column(String(50), nullable=True)  # e.g., "30 seconds", "10 minutes"
    aspect_ratio = Column(String(20), default="16:9")
    resolution = Column(String(20), nullable=True)  # 1920x1080, 1080x1920, etc.
    video_format = Column(String(20), default="mp4")
    fps = Column(Integer, default=30)
    
    # Audio
    music_style = Column(String(255), nullable=True)
    background_music_id = Column(String(100), nullable=True)
    sound_effects = Column(JSON, default=list)
    
    # Branding
    logo_placement = Column(JSON, nullable=True)
    watermark_enabled = Column(Boolean, default=False)
    
    # AI Settings
    ai_provider = Column(String(50), nullable=True)  # Preferred AI provider for this template
    model_settings = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    organization = relationship("Organization")
    channel_profile = relationship("ChannelProfile", back_populates="production_templates")
    playlists = relationship("Playlist", back_populates="production_template")
    episodes = relationship("Episode", back_populates="production_template")
    content_jobs = relationship("ContentJob", back_populates="production_template")
    
    __table_args__ = (
        Index('idx_template_channel', 'channel_profile_id'),
        Index('idx_template_default', 'is_default'),
    )
    
    def __repr__(self):
        return f"<ProductionTemplate(id={self.id}, name='{self.name}')>"


class ContentJob(TenantMixin, Base):
    """
    ContentJob model - Production execution tracking.
    
    Tracks actual production work including AI provider usage,
    costs, timing, and execution status.
    """
    __tablename__ = "content_jobs"
    
    # Identification
    job_name = Column(String(255), nullable=False)
    job_type = Column(String(100), nullable=False)  # research, script, video, voice, etc.
    
    # Status tracking
    status = Column(SQLEnum(ContentJobStatus), default=ContentJobStatus.PENDING, index=True)
    
    # Foreign keys
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    production_template_id = Column(Integer, ForeignKey("production_templates.id", ondelete="SET NULL"), nullable=True)
    
    # AI Provider details
    ai_provider = Column(String(50), nullable=True)  # openai, anthropic, ollama, etc.
    model_name = Column(String(100), nullable=True)  # gpt-4, claude-3, etc.
    
    # Token/Cost tracking
    input_tokens = Column(BigInteger, default=0)
    output_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)
    cost_usd = Column(Float, default=0.0)
    
    # Execution tracking
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Retry handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Input/Output
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    
    # Agent reference
    agent_name = Column(String(100), nullable=True, index=True)
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    organization = relationship("Organization")
    episode = relationship("Episode", back_populates="content_jobs")
    production_template = relationship("ProductionTemplate", back_populates="content_jobs")
    approval_requests = relationship("ApprovalRequest", back_populates="content_job")
    
    __table_args__ = (
        Index('idx_job_episode', 'episode_id'),
        Index('idx_job_status', 'status'),
        Index('idx_job_agent', 'agent_name'),
        Index('idx_job_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ContentJob(id={self.id}, name='{self.job_name}', status='{self.status}')>"


# =============================================================================
# MEDIA MODELS
# =============================================================================

class Asset(TenantMixin, Base):
    """
    Asset model - Media file management.
    
    Manages all media assets including images, videos, audio, subtitles,
    scripts, and thumbnails with metadata and storage references.
    """
    __tablename__ = "assets"
    
    # Identification
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    
    # Type
    asset_type = Column(SQLEnum(AssetType), nullable=False, index=True)
    mime_type = Column(String(100), nullable=True)
    
    # Foreign keys
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Storage
    storage_provider = Column(String(50), nullable=True)  # s3, gcs, local, etc.
    storage_bucket = Column(String(255), nullable=True)
    storage_path = Column(String(500), nullable=True)
    storage_key = Column(String(255), nullable=True, index=True)  # Unique storage identifier
    storage_url = Column(String(500), nullable=True)  # Public or signed URL
    
    # File info
    file_size_bytes = Column(BigInteger, nullable=True)
    duration_seconds = Column(Float, nullable=True)  # For audio/video
    dimensions = Column(String(20), nullable=True)  # Width x Height for images/video
    
    # Processing status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_metadata = Column(JSON, nullable=True)
    
    # Thumbnails/Previews
    thumbnail_url = Column(String(500), nullable=True)
    preview_url = Column(String(500), nullable=True)
    
    # Metadata
    alt_text = Column(String(500), nullable=True)
    tags = Column(JSON, default=list)
    file_metadata = Column(JSON, default=dict)  # Additional metadata from storage provider (renamed from 'metadata')
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    organization = relationship("Organization")
    episode = relationship("Episode", back_populates="assets")
    lifecycle_transitions = relationship("AssetLifecycleTransition", back_populates="asset")
    audit_logs = relationship("AssetAuditLog", back_populates="asset")
    quality_scores = relationship("MediaQualityScore", back_populates="asset")
    approval_requests = relationship("ApprovalRequest", back_populates="asset")
    
    __table_args__ = (
        Index('idx_asset_episode', 'episode_id'),
        Index('idx_asset_type', 'asset_type'),
        Index('idx_asset_storage', 'storage_provider', 'storage_bucket'),
    )
    
    def __repr__(self):
        return f"<Asset(id={self.id}, filename='{self.filename}', type='{self.asset_type}')>"


# =============================================================================
# AI OPERATIONS MODELS
# =============================================================================

class AgentExecution(TenantMixin, Base):
    """
    AgentExecution model - AI agent execution tracking.
    
    Records individual agent executions including inputs, outputs,
    status, duration, and errors for observability and debugging.
    """
    __tablename__ = "agent_executions"
    
    # Identification
    execution_id = Column(String(100), unique=True, nullable=True, index=True)  # UUID for tracing
    
    # Agent info
    agent_name = Column(String(100), nullable=False, index=True)
    agent_version = Column(String(20), nullable=True)
    
    # Status
    status = Column(SQLEnum(AgentExecutionStatus), default=AgentExecutionStatus.PENDING, index=True)
    
    # Foreign keys
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    content_job_id = Column(Integer, ForeignKey("content_jobs.id", ondelete="SET NULL"), nullable=True)
    
    # Execution data
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)  # Alias for completed_at
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time = Column(Float, nullable=True)  # Alias for duration_seconds
    duration_seconds = Column(Float, nullable=True)
    
    # Token usage tracking
    token_usage = Column(BigInteger, default=0)  # Alias for total_tokens
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_stack_trace = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # AI Provider details
    ai_provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)
    prompt_tokens = Column(BigInteger, default=0)
    completion_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)
    cost_usd = Column(Float, default=0.0)  # Cost tracking
    
    # Retry info
    retry_count = Column(Integer, default=0)
    parent_execution_id = Column(Integer, nullable=True)  # Reference to previous attempt
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Relationships
    organization = relationship("Organization")
    episode = relationship("Episode", back_populates="agent_executions")
    content_job = relationship("ContentJob")
    approval_requests = relationship("ApprovalRequest", back_populates="agent_execution")
    
    __table_args__ = (
        Index('idx_agent_episode', 'episode_id'),
        Index('idx_agent_status', 'status'),
        Index('idx_agent_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AgentExecution(id={self.id}, agent='{self.agent_name}', status='{self.status}')>"


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES (Optional)
# =============================================================================
# These aliases help during migration from v1 to v2

# Old ContentProfile -> New ChannelProfile
# Old Project -> Can be mapped to Episode or kept separate during migration
# Old WorkflowStage -> Now tracked via ContentJob and AgentExecution


# =============================================================================
# RENDERING MODELS (Phase 8A)
# =============================================================================

class RenderingJobStatus(str, enum.Enum):
    """Rendering job lifecycle status."""
    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RenderingJob(TenantMixin, Base):
    """
    RenderingJob model - Video rendering execution tracking.
    
    Tracks rendering jobs for video production including FFmpeg operations,
    transcoding, and output generation.
    """
    __tablename__ = "rendering_jobs"
    
    # Identification
    job_id = Column(String(100), unique=True, nullable=True, index=True)  # UUID for external reference
    name = Column(String(255), nullable=False)
    job_type = Column(String(100), nullable=False)  # transcode, merge, render, etc.
    
    # Status
    status = Column(SQLEnum(RenderingJobStatus), default=RenderingJobStatus.CREATED, index=True)
    progress = Column(Integer, default=0)  # 0-100 percentage
    
    # Foreign keys
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    composition_id = Column(Integer, ForeignKey("video_compositions.id", ondelete="SET NULL"), nullable=True)
    
    # Input/Output
    input_files = Column(JSON, default=list)  # List of input file paths/keys
    output_format = Column(String(50), nullable=True)  # mp4, webm, etc.
    
    # Parameters
    parameters = Column(JSON, default=dict)  # Rendering parameters
    priority = Column(Integer, default=0)  # Job priority
    
    # Execution tracking
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Retry handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Cost tracking
    compute_time_seconds = Column(Float, nullable=True)
    worker_cost_usd = Column(Float, default=0.0)
    
    # Metadata
    job_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' to avoid reserved word conflict
    
    # Relationships
    organization = relationship("Organization")
    episode = relationship("Episode")
    composition = relationship("VideoComposition", back_populates="rendering_jobs")
    outputs = relationship("RenderOutput", back_populates="rendering_job", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_rendering_job_org', 'organization_id'),
        Index('idx_rendering_job_status', 'status'),
        Index('idx_rendering_job_episode', 'episode_id'),
        Index('idx_rendering_job_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<RenderingJob(id={self.id}, name='{self.name}', status='{self.status}')>"


class VideoComposition(TenantMixin, Base):
    """
    VideoComposition model - Video editing composition definition.
    
    Defines the structure of a video composition including clips,
    transitions, audio tracks, and subtitles.
    """
    __tablename__ = "video_compositions"
    
    # Identification
    composition_id = Column(String(100), unique=True, nullable=True, index=True)  # UUID
    name = Column(String(255), nullable=False)
    
    # Status
    status = Column(String(50), default="draft")  # draft, processing, completed, failed
    
    # Foreign keys
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Composition data
    clips = Column(JSON, default=list)  # List of clip definitions
    transitions = Column(JSON, default=list)  # List of transition definitions
    audio_tracks = Column(JSON, default=list)  # List of audio track definitions
    subtitles = Column(JSON, default=list)  # List of subtitle track definitions
    
    # Output settings
    resolution = Column(String(20), default="1920x1080")  # Width x Height
    fps = Column(Float, default=30.0)  # Frames per second
    
    # Duration
    duration_seconds = Column(Float, nullable=True)
    
    # Metadata
    composition_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' to avoid reserved word conflict
    
    # Relationships
    organization = relationship("Organization")
    episode = relationship("Episode")
    rendering_jobs = relationship("RenderingJob", back_populates="composition")
    
    __table_args__ = (
        Index('idx_composition_org', 'organization_id'),
        Index('idx_composition_episode', 'episode_id'),
        Index('idx_composition_status', 'status'),
    )
    
    def __repr__(self):
        return f"<VideoComposition(id={self.id}, name='{self.name}')>"


class RenderOutput(TenantMixin, Base):
    """
    RenderOutput model - Rendering output file tracking.
    
    Tracks output files generated by rendering jobs including
    videos, thumbnails, subtitles, and intermediate files.
    """
    __tablename__ = "render_outputs"
    
    # Identification
    output_id = Column(String(100), unique=True, nullable=True, index=True)  # UUID
    output_type = Column(String(50), nullable=False)  # video, thumbnail, subtitle, intermediate
    
    # Foreign keys
    rendering_job_id = Column(Integer, ForeignKey("rendering_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Storage
    storage_key = Column(String(500), nullable=False)  # Storage path/key
    storage_url = Column(String(500), nullable=True)  # Access URL
    
    # File info
    file_size_bytes = Column(BigInteger, nullable=True)
    duration_seconds = Column(Float, nullable=True)  # For video/audio outputs
    resolution = Column(String(20), nullable=True)  # For video/image outputs
    
    # Checksums
    checksum_md5 = Column(String(64), nullable=True)
    checksum_sha256 = Column(String(128), nullable=True)
    
    # Metadata
    output_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' to avoid reserved word conflict
    
    # Relationships
    organization = relationship("Organization")
    rendering_job = relationship("RenderingJob", back_populates="outputs")
    
    __table_args__ = (
        Index('idx_render_output_org', 'organization_id'),
        Index('idx_render_output_job', 'rendering_job_id'),
        Index('idx_render_output_type', 'output_type'),
    )
    
    def __repr__(self):
        return f"<RenderOutput(id={self.id}, type='{self.output_type}', job_id={self.rendering_job_id})>"


# =============================================================================
# PUBLISHING & PLATFORM INTEGRATION MODELS
# =============================================================================

class PublishingCredential(TenantMixin, Base):
    """
    PublishingCredential model - Encrypted platform credentials.
    
    Stores OAuth tokens, API keys, and other authentication credentials
    for external publishing platforms with encryption at rest.
    """
    __tablename__ = "publishing_credentials"
    
    # Platform identification
    platform = Column(String(50), nullable=False, index=True)  # e.g., 'youtube', 'vimeo'
    credential_type = Column(String(50), nullable=False)  # e.g., 'oauth2', 'api_key'
    account_name = Column(String(255), nullable=True)  # Human-readable account identifier
    
    # Encrypted credential data
    encrypted_data = Column(Text, nullable=False)  # JSON blob, encrypted
    
    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For expiring tokens
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Extra metadata
    extra_data = Column(JSON, default=dict)
    
    __table_args__ = (
        Index('idx_cred_org_platform', 'organization_id', 'platform'),
        Index('idx_cred_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<PublishingCredential(id={self.id}, platform='{self.platform}', org={self.organization_id})>"


class PublishingState(TenantMixin, Base):
    """
    PublishingState model - Persistent publishing operation state.
    
    Tracks the state machine of publishing operations across platforms,
    enabling recovery from failures and audit trails.
    """
    __tablename__ = "publishing_states"
    
    # Foreign keys
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id = Column(Integer, ForeignKey("publishing_credentials.id"), nullable=True)
    
    # Platform identification
    platform = Column(String(50), nullable=False, index=True)
    
    # State machine
    state = Column(String(50), nullable=False, default="pending", index=True)  # pending, uploading, processing, published, failed, retrying
    previous_state = Column(String(50), nullable=True)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timestamps
    transitioned_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    state_metadata = Column(JSON, default=dict)  # Platform-specific publish data, video IDs, URLs
    external_id = Column(String(255), nullable=True)  # Platform's video/content ID
    external_url = Column(String(500), nullable=True)
    
    __table_args__ = (
        Index('idx_pub_state_episode', 'episode_id'),
        Index('idx_pub_state_org_platform', 'organization_id', 'platform'),
        Index('idx_pub_state_state', 'state'),
    )
    
    def __repr__(self):
        return f"<PublishingState(id={self.id}, episode={self.episode_id}, platform='{self.platform}', state='{self.state}')>"


class PlatformWebhook(TenantMixin, Base):
    """
    PlatformWebhook model - Webhook configurations for platform callbacks.
    
    Manages webhook endpoints for receiving events from external platforms
    such as publish completion, analytics updates, etc.
    """
    __tablename__ = "platform_webhooks"
    
    # Platform identification
    platform = Column(String(50), nullable=False, index=True)
    
    # Webhook configuration
    endpoint_url = Column(String(500), nullable=False)
    secret_hash = Column(String(255), nullable=False)  # Hashed signing secret
    events = Column(JSON, default=list)  # List of event types to subscribe to
    
    # Associated credential (optional)
    credential_id = Column(Integer, ForeignKey("publishing_credentials.id"), nullable=True)
    
    # Verification status
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_token = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Delivery tracking
    last_delivery_at = Column(DateTime(timezone=True), nullable=True)
    last_delivery_success = Column(Boolean, nullable=True)
    last_response_code = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_webhook_org_platform', 'organization_id', 'platform'),
        Index('idx_webhook_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<PlatformWebhook(id={self.id}, platform='{self.platform}', url='{self.endpoint_url}')>"


class PlatformRateLimit(TenantMixin, Base):
    """
    PlatformRateLimit model - API rate limit tracking per platform.
    
    Tracks request counts and enforces rate limits to prevent API throttling
    from external platforms.
    """
    __tablename__ = "platform_rate_limits"
    
    # Platform identification
    platform = Column(String(50), nullable=False, index=True)
    
    # Rate limit configuration
    requests_per_minute = Column(Integer, default=60)
    requests_per_hour = Column(Integer, nullable=True)
    requests_per_day = Column(Integer, nullable=True)
    
    # Current counters
    request_count_this_minute = Column(Integer, default=0)
    request_count_this_hour = Column(Integer, default=0)
    request_count_today = Column(Integer, default=0)
    
    # Tracking
    last_request_at = Column(DateTime(timezone=True), nullable=True)
    last_reset_date = Column(DateTime(timezone=True), nullable=True)  # Date when counters were reset
    
    __table_args__ = (
        Index('idx_rate_limit_org_platform', 'organization_id', 'platform'),
    )
    
    def __repr__(self):
        return f"<PlatformRateLimit(id={self.id}, platform='{self.platform}', org={self.organization_id})>"


class AnalyticsJob(TenantMixin, Base):
    """
    AnalyticsJob model - Scheduled analytics collection jobs.
    
    Supports background jobs for collecting analytics data from platforms
    on a scheduled basis.
    """
    __tablename__ = "analytics_jobs"
    
    # Job configuration
    job_type = Column(String(50), nullable=False, index=True)  # e.g., 'video_analytics', 'channel_analytics'
    platform = Column(String(50), nullable=True, index=True)  # Optional platform filter
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    priority = Column(Integer, default=0)  # Higher = more urgent
    
    # Execution state
    status = Column(String(50), default="pending", index=True)  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Retry tracking
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Results
    result = Column(JSON, nullable=True)  # Collected analytics data
    job_metadata = Column(JSON, default=dict)
    
    __table_args__ = (
        Index('idx_analytics_job_status', 'status', 'scheduled_at'),
        Index('idx_analytics_job_org', 'organization_id'),
    )
    
    def __repr__(self):
        return f"<AnalyticsJob(id={self.id}, type='{self.job_type}', status='{self.status}')>"


