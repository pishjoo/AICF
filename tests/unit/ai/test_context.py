"""
Unit tests for AI Context System.

Tests cover:
- Context creation
- ContextBuilder
- System prompt generation
- Serialization/deserialization
"""

import pytest
from datetime import datetime

from app.ai.context.context import (
    AIContext,
    ContextBuilder,
    OrganizationInfo,
    ChannelInfo,
    AudienceInfo,
    BrandRules,
    ContentReference,
    Constraints,
)


class TestOrganizationInfo:
    """Tests for OrganizationInfo."""
    
    def test_create_organization_info(self):
        """Test creating organization info."""
        org = OrganizationInfo(
            id=1,
            name="Test Org",
            slug="test-org"
        )
        
        assert org.id == 1
        assert org.name == "Test Org"
        assert org.slug == "test-org"
        assert org.subscription_plan == "free"
        assert org.settings == {}


class TestChannelInfo:
    """Tests for ChannelInfo."""
    
    def test_create_channel_info(self):
        """Test creating channel info."""
        channel = ChannelInfo(
            id=1,
            name="My YouTube Channel",
            platform="youtube",
            handle="@mychannel"
        )
        
        assert channel.id == 1
        assert channel.name == "My YouTube Channel"
        assert channel.platform == "youtube"
        assert channel.handle == "@mychannel"


class TestAudienceInfo:
    """Tests for AudienceInfo."""
    
    def test_create_audience_info(self):
        """Test creating audience info."""
        audience = AudienceInfo(
            demographics={"age_range": "25-34", "location": "US"},
            interests=["technology", "AI"],
            tone_preferences=["professional", "friendly"]
        )
        
        assert audience.demographics["age_range"] == "25-34"
        assert "technology" in audience.interests
        assert "professional" in audience.tone_preferences


class TestBrandRules:
    """Tests for BrandRules."""
    
    def test_create_brand_rules(self):
        """Test creating brand rules."""
        rules = BrandRules(
            brand_voice="Professional yet approachable",
            prohibited_words=["cheap", "free"],
            do_not_say=["We are the best", "Guaranteed results"]
        )
        
        assert rules.brand_voice == "Professional yet approachable"
        assert "cheap" in rules.prohibited_words
        assert "Guaranteed results" in rules.do_not_say


class TestConstraints:
    """Tests for Constraints."""
    
    def test_create_constraints(self):
        """Test creating constraints."""
        constraints = Constraints(
            max_length=500,
            min_length=100,
            format="markdown",
            language="en"
        )
        
        assert constraints.max_length == 500
        assert constraints.min_length == 100
        assert constraints.format == "markdown"
        assert constraints.language == "en"


class TestContentReference:
    """Tests for ContentReference."""
    
    def test_create_content_reference(self):
        """Test creating content reference."""
        now = datetime.utcnow()
        ref = ContentReference(
            id=1,
            type="episode",
            title="My First Episode",
            url="https://example.com/video",
            summary="A great episode about AI",
            created_at=now
        )
        
        assert ref.id == 1
        assert ref.type == "episode"
        assert ref.title == "My First Episode"
        assert ref.url == "https://example.com/video"


class TestAIContext:
    """Tests for AIContext class."""
    
    def test_create_context_minimal(self):
        """Test creating context with minimal required data."""
        org = OrganizationInfo(id=1, name="Test", slug="test")
        context = AIContext(organization=org)
        
        assert context.organization.id == 1
        assert context.channel is None
        assert context.audience is not None  # Default created
        assert context.brand_rules is not None  # Default created
        assert context.content_references == []
    
    def test_create_context_full(self):
        """Test creating context with all components."""
        org = OrganizationInfo(id=1, name="Test Org", slug="test-org")
        channel = ChannelInfo(id=1, name="YouTube", platform="youtube")
        audience = AudienceInfo(interests=["tech"])
        brand_rules = BrandRules(brand_voice="Friendly")
        constraints = Constraints(max_length=100)
        
        context = AIContext(
            organization=org,
            channel=channel,
            audience=audience,
            brand_rules=brand_rules,
            constraints=constraints
        )
        
        assert context.organization.name == "Test Org"
        assert context.channel.platform == "youtube"
        assert context.audience.interests == ["tech"]
        assert context.brand_rules.brand_voice == "Friendly"
        assert context.constraints.max_length == 100
    
    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        org = OrganizationInfo(id=1, name="Test", slug="test")
        channel = ChannelInfo(id=1, name="Channel", platform="youtube")
        
        context = AIContext(organization=org, channel=channel)
        data = context.to_dict()
        
        assert data["organization"]["id"] == 1
        assert data["organization"]["name"] == "Test"
        assert data["channel"]["platform"] == "youtube"
        assert "brand_rules" in data
        assert "constraints" in data
    
    def test_get_system_prompt(self):
        """Test generating system prompt from context."""
        org = OrganizationInfo(id=1, name="Acme Corp", slug="acme")
        channel = ChannelInfo(id=1, name="Main Channel", platform="youtube")
        brand_rules = BrandRules(
            brand_voice="Professional",
            prohibited_words=["bad", "ugly"],
            do_not_say=["We suck"]
        )
        audience = AudienceInfo(tone_preferences=["friendly", "helpful"])
        constraints = Constraints(max_length=500, format="json")
        
        context = AIContext(
            organization=org,
            channel=channel,
            brand_rules=brand_rules,
            audience=audience,
            constraints=constraints
        )
        
        prompt = context.get_system_prompt()
        
        assert "Acme Corp" in prompt
        assert "Main Channel" in prompt
        assert "youtube" in prompt
        assert "Professional" in prompt
        assert "bad" in prompt or "ugly" in prompt
        assert "friendly" in prompt
        assert "500" in prompt
        assert "json" in prompt
    
    def test_context_from_dict(self):
        """Test creating context from dictionary."""
        data = {
            "organization": {
                "id": 1,
                "name": "Test Org",
                "slug": "test-org",
                "subscription_plan": "pro"
            },
            "channel": {
                "id": 1,
                "name": "Test Channel",
                "platform": "tiktok",
                "handle": "@test"
            },
            "audience": {
                "demographics": {"age": "25-34"},
                "interests": ["music"],
                "tone_preferences": ["casual"]
            },
            "brand_rules": {
                "brand_voice": "Casual and fun",
                "prohibited_words": [],
                "required_elements": [],
                "style_guide": {},
                "compliance_rules": [],
                "do_not_say": []
            },
            "content_references": [],
            "constraints": {
                "max_length": None,
                "min_length": None,
                "format": None,
                "language": "es",
                "reading_level": None,
                "time_period": None,
                "custom_constraints": []
            }
        }
        
        context = AIContext.from_dict(data)
        
        assert context.organization.name == "Test Org"
        assert context.channel.platform == "tiktok"
        assert context.audience.interests == ["music"]
        assert context.constraints.language == "es"


class TestContextBuilder:
    """Tests for ContextBuilder fluent interface."""
    
    def test_build_context_step_by_step(self):
        """Test building context incrementally."""
        org = OrganizationInfo(id=1, name="Test", slug="test")
        channel = ChannelInfo(id=1, name="Channel", platform="youtube")
        
        builder = ContextBuilder()
        context = (builder
            .with_organization(org)
            .with_channel(channel)
            .add_custom_data("key", "value")
            .build())
        
        assert context.organization.id == 1
        assert context.channel.platform == "youtube"
        assert context.custom_data["key"] == "value"
    
    def test_build_without_organization_raises_error(self):
        """Test that building without organization raises error."""
        builder = ContextBuilder()
        
        with pytest.raises(ValueError, match="Organization is required"):
            builder.build()
    
    def test_build_with_all_components(self):
        """Test building complete context."""
        org = OrganizationInfo(id=1, name="Org", slug="org")
        channel = ChannelInfo(id=1, name="Ch", platform="yt")
        audience = AudienceInfo(interests=["a"])
        brand_rules = BrandRules(brand_voice="Voice")
        constraints = Constraints(max_length=100)
        ref = ContentReference(id=1, type="ep", title="Title")
        
        builder = ContextBuilder()
        context = (builder
            .with_organization(org)
            .with_channel(channel)
            .with_audience(audience)
            .with_brand_rules(brand_rules)
            .add_content_reference(ref)
            .with_constraints(constraints)
            .build())
        
        assert len(context.content_references) == 1
        assert context.content_references[0].title == "Title"
