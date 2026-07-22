"""
AI Context System

This module implements the AIContext object that contains all contextual
information needed for AI operations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class OrganizationInfo:
    """Organization information for context."""
    id: int
    name: str
    slug: str
    subscription_plan: str = "free"
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelInfo:
    """Channel information for context."""
    id: int
    name: str
    platform: str  # youtube, tiktok, instagram, etc.
    handle: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudienceInfo:
    """Audience information for context."""
    demographics: Dict[str, Any] = field(default_factory=dict)
    interests: List[str] = field(default_factory=list)
    tone_preferences: List[str] = field(default_factory=list)
    content_preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrandRules:
    """Brand rules and guidelines for content generation."""
    brand_voice: str = ""
    prohibited_words: List[str] = field(default_factory=list)
    required_elements: List[str] = field(default_factory=list)
    style_guide: Dict[str, Any] = field(default_factory=dict)
    compliance_rules: List[str] = field(default_factory=list)
    do_not_say: List[str] = field(default_factory=list)


@dataclass
class ContentReference:
    """Reference to previous content."""
    id: int
    type: str  # episode, playlist, script, etc.
    title: str
    url: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Constraints:
    """Constraints for AI generation."""
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    format: Optional[str] = None  # json, markdown, plain text
    language: str = "en"
    reading_level: Optional[str] = None
    time_period: Optional[str] = None
    custom_constraints: List[str] = field(default_factory=list)


class AIContext:
    """
    AI Context object containing all contextual information for AI operations.
    
    This object aggregates all relevant context that AI agents need to
    generate appropriate content for a specific organization and channel.
    
    Attributes:
        organization: Organization information
        channel: Channel information (optional)
        audience: Audience information
        brand_rules: Brand guidelines and rules
        content_references: References to previous content
        constraints: Generation constraints
        custom_data: Additional custom context data
    """
    
    def __init__(
        self,
        organization: OrganizationInfo,
        channel: Optional[ChannelInfo] = None,
        audience: Optional[AudienceInfo] = None,
        brand_rules: Optional[BrandRules] = None,
        content_references: Optional[List[ContentReference]] = None,
        constraints: Optional[Constraints] = None,
        custom_data: Optional[Dict[str, Any]] = None,
    ):
        self.organization = organization
        self.channel = channel
        self.audience = audience or AudienceInfo()
        self.brand_rules = brand_rules or BrandRules()
        self.content_references = content_references or []
        self.constraints = constraints or Constraints()
        self.custom_data = custom_data or {}
        self._created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary format for API requests."""
        return {
            "organization": {
                "id": self.organization.id,
                "name": self.organization.name,
                "slug": self.organization.slug,
                "subscription_plan": self.organization.subscription_plan,
                "settings": self.organization.settings,
            },
            "channel": {
                "id": self.channel.id if self.channel else None,
                "name": self.channel.name if self.channel else None,
                "platform": self.channel.platform if self.channel else None,
                "handle": self.channel.handle if self.channel else None,
                "settings": self.channel.settings if self.channel else {},
            } if self.channel else None,
            "audience": {
                "demographics": self.audience.demographics,
                "interests": self.audience.interests,
                "tone_preferences": self.audience.tone_preferences,
                "content_preferences": self.audience.content_preferences,
            },
            "brand_rules": {
                "brand_voice": self.brand_rules.brand_voice,
                "prohibited_words": self.brand_rules.prohibited_words,
                "required_elements": self.brand_rules.required_elements,
                "style_guide": self.brand_rules.style_guide,
                "compliance_rules": self.brand_rules.compliance_rules,
                "do_not_say": self.brand_rules.do_not_say,
            },
            "content_references": [
                {
                    "id": ref.id,
                    "type": ref.type,
                    "title": ref.title,
                    "url": ref.url,
                    "summary": ref.summary,
                    "created_at": ref.created_at.isoformat() if ref.created_at else None,
                }
                for ref in self.content_references
            ],
            "constraints": {
                "max_length": self.constraints.max_length,
                "min_length": self.constraints.min_length,
                "format": self.constraints.format,
                "language": self.constraints.language,
                "reading_level": self.constraints.reading_level,
                "time_period": self.constraints.time_period,
                "custom_constraints": self.constraints.custom_constraints,
            },
            "custom_data": self.custom_data,
        }
    
    def get_system_prompt(self) -> str:
        """
        Generate a system prompt from the context.
        
        Returns:
            A formatted system prompt string
        """
        parts = []
        
        # Organization context
        parts.append(f"You are assisting {self.organization.name}.")
        
        # Channel context
        if self.channel:
            parts.append(
                f"Content is for the '{self.channel.name}' channel on {self.channel.platform}."
            )
        
        # Brand voice
        if self.brand_rules.brand_voice:
            parts.append(f"Brand voice: {self.brand_rules.brand_voice}")
        
        # Prohibited words
        if self.brand_rules.prohibited_words:
            parts.append(
                f"Do not use these words: {', '.join(self.brand_rules.prohibited_words)}"
            )
        
        # Do not say
        if self.brand_rules.do_not_say:
            parts.append(f"Avoid saying: {'; '.join(self.brand_rules.do_not_say)}")
        
        # Audience preferences
        if self.audience.tone_preferences:
            parts.append(f"Use this tone: {', '.join(self.audience.tone_preferences)}")
        
        # Constraints
        constraint_parts = []
        if self.constraints.max_length:
            constraint_parts.append(f"maximum {self.constraints.max_length} characters")
        if self.constraints.min_length:
            constraint_parts.append(f"minimum {self.constraints.min_length} characters")
        if self.constraints.format:
            constraint_parts.append(f"format as {self.constraints.format}")
        if self.constraints.language != "en":
            constraint_parts.append(f"respond in {self.constraints.language}")
        
        if constraint_parts:
            parts.append(f"Constraints: {', '.join(constraint_parts)}")
        
        return "\n".join(parts)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIContext":
        """Create AIContext from dictionary."""
        org_data = data.get("organization", {})
        organization = OrganizationInfo(
            id=org_data.get("id"),
            name=org_data.get("name"),
            slug=org_data.get("slug"),
            subscription_plan=org_data.get("subscription_plan", "free"),
            settings=org_data.get("settings", {}),
        )
        
        channel_data = data.get("channel")
        channel = None
        if channel_data and channel_data.get("id"):
            channel = ChannelInfo(
                id=channel_data.get("id"),
                name=channel_data.get("name"),
                platform=channel_data.get("platform"),
                handle=channel_data.get("handle"),
                settings=channel_data.get("settings", {}),
            )
        
        audience_data = data.get("audience", {})
        audience = AudienceInfo(
            demographics=audience_data.get("demographics", {}),
            interests=audience_data.get("interests", []),
            tone_preferences=audience_data.get("tone_preferences", []),
            content_preferences=audience_data.get("content_preferences", {}),
        )
        
        brand_data = data.get("brand_rules", {})
        brand_rules = BrandRules(
            brand_voice=brand_data.get("brand_voice", ""),
            prohibited_words=brand_data.get("prohibited_words", []),
            required_elements=brand_data.get("required_elements", []),
            style_guide=brand_data.get("style_guide", {}),
            compliance_rules=brand_data.get("compliance_rules", []),
            do_not_say=brand_data.get("do_not_say", []),
        )
        
        ref_list = data.get("content_references", [])
        content_references = []
        for ref_data in ref_list:
            content_references.append(ContentReference(
                id=ref_data.get("id"),
                type=ref_data.get("type"),
                title=ref_data.get("title"),
                url=ref_data.get("url"),
                summary=ref_data.get("summary"),
                created_at=datetime.fromisoformat(ref_data["created_at"]) if ref_data.get("created_at") else None,
            ))
        
        constraint_data = data.get("constraints", {})
        constraints = Constraints(
            max_length=constraint_data.get("max_length"),
            min_length=constraint_data.get("min_length"),
            format=constraint_data.get("format"),
            language=constraint_data.get("language", "en"),
            reading_level=constraint_data.get("reading_level"),
            time_period=constraint_data.get("time_period"),
            custom_constraints=constraint_data.get("custom_constraints", []),
        )
        
        return cls(
            organization=organization,
            channel=channel,
            audience=audience,
            brand_rules=brand_rules,
            content_references=content_references,
            constraints=constraints,
            custom_data=data.get("custom_data"),
        )


class ContextBuilder:
    """
    Builder class for constructing AIContext objects.
    
    Provides a fluent interface for building complex contexts.
    """
    
    def __init__(self):
        self._organization: Optional[OrganizationInfo] = None
        self._channel: Optional[ChannelInfo] = None
        self._audience: Optional[AudienceInfo] = None
        self._brand_rules: Optional[BrandRules] = None
        self._content_references: List[ContentReference] = []
        self._constraints: Optional[Constraints] = None
        self._custom_data: Dict[str, Any] = {}
    
    def with_organization(self, org: OrganizationInfo) -> "ContextBuilder":
        """Set organization information."""
        self._organization = org
        return self
    
    def with_channel(self, channel: ChannelInfo) -> "ContextBuilder":
        """Set channel information."""
        self._channel = channel
        return self
    
    def with_audience(self, audience: AudienceInfo) -> "ContextBuilder":
        """Set audience information."""
        self._audience = audience
        return self
    
    def with_brand_rules(self, rules: BrandRules) -> "ContextBuilder":
        """Set brand rules."""
        self._brand_rules = rules
        return self
    
    def add_content_reference(self, ref: ContentReference) -> "ContextBuilder":
        """Add a content reference."""
        self._content_references.append(ref)
        return self
    
    def with_constraints(self, constraints: Constraints) -> "ContextBuilder":
        """Set constraints."""
        self._constraints = constraints
        return self
    
    def add_custom_data(self, key: str, value: Any) -> "ContextBuilder":
        """Add custom data."""
        self._custom_data[key] = value
        return self
    
    def build(self) -> AIContext:
        """Build the AIContext object."""
        if not self._organization:
            raise ValueError("Organization is required")
        
        return AIContext(
            organization=self._organization,
            channel=self._channel,
            audience=self._audience,
            brand_rules=self._brand_rules,
            content_references=self._content_references,
            constraints=self._constraints,
            custom_data=self._custom_data if self._custom_data else None,
        )
