"""
Agent Registry

Central registry for all workflow agents.
Manages agent instantiation and lookup by stage type.
"""

from typing import Dict, Type, Optional, List
import logging

from .base import BaseAgent, AgentContext, AgentResult


class AgentRegistry:
    """
    Registry for managing AI agents.
    
    Provides:
    - Agent registration by stage type
    - Agent lookup and instantiation
    - Default mock agents for development
    
    Registered agents:
    - IdeaAgent
    - ResearchAgent
    - ScriptAgent
    - StoryboardAgent
    - AssetAgent
    - VideoAgent (for video_production)
    - SEOAgent
    - PublishAgent
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}
        self.logger = logging.getLogger("agent_registry")
    
    def register(self, stage_type: str, agent: BaseAgent) -> None:
        """
        Register an agent instance for a stage type.
        
        Args:
            stage_type: The workflow stage type (e.g., "idea", "script").
            agent: Agent instance to register.
        """
        self._agents[stage_type] = agent
        self.logger.info(f"Registered agent '{agent.name}' for stage '{stage_type}'")
    
    def register_class(self, stage_type: str, agent_class: Type[BaseAgent]) -> None:
        """
        Register an agent class for lazy instantiation.
        
        Args:
            stage_type: The workflow stage type.
            agent_class: Agent class to register.
        """
        self._agent_classes[stage_type] = agent_class
        self.logger.info(f"Registered agent class '{agent_class.__name__}' for stage '{stage_type}'")
    
    def get_agent(self, stage_type: str) -> Optional[BaseAgent]:
        """
        Get an agent for a stage type.
        
        Args:
            stage_type: The workflow stage type.
            
        Returns:
            Agent instance or None if not registered.
        """
        # Return existing instance
        if stage_type in self._agents:
            return self._agents[stage_type]
        
        # Instantiate from class if registered
        if stage_type in self._agent_classes:
            agent = self._agent_classes[stage_type]()
            self._agents[stage_type] = agent
            return agent
        
        return None
    
    def get_all_agents(self) -> Dict[str, BaseAgent]:
        """Get all registered agents."""
        # Ensure all classes are instantiated
        for stage_type, agent_class in list(self._agent_classes.items()):
            if stage_type not in self._agents:
                self._agents[stage_type] = agent_class()
        
        return self._agents.copy()
    
    def is_registered(self, stage_type: str) -> bool:
        """Check if an agent is registered for a stage type."""
        return stage_type in self._agents or stage_type in self._agent_classes
    
    def unregister(self, stage_type: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            stage_type: The workflow stage type.
            
        Returns:
            True if agent was unregistered.
        """
        if stage_type in self._agents:
            del self._agents[stage_type]
            self.logger.info(f"Unregistered agent for stage '{stage_type}'")
            return True
        if stage_type in self._agent_classes:
            del self._agent_classes[stage_type]
            self.logger.info(f"Unregistered agent class for stage '{stage_type}'")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
        self._agent_classes.clear()
        self.logger.info("Cleared all registered agents")


# Global registry instance
_default_registry = AgentRegistry()


def get_registry() -> AgentRegistry:
    """Get the default agent registry."""
    return _default_registry


# =============================================================================
# MOCK AGENT IMPLEMENTATIONS
# =============================================================================

class MockIdeaAgent(BaseAgent):
    """Mock agent for IDEA stage."""
    name = "idea_agent"
    description = "Generates video ideas based on channel profile"
    stage_type = "idea"
    
    def execute(self, context: AgentContext) -> AgentResult:
        """Generate mock idea output."""
        self.log_execution("Generating idea...")
        return AgentResult(
            success=True,
            output={
                "idea": f"Video idea for {context.channel_profile.name}",
                "concept": "Educational content with engaging visuals",
                "hook": "Start with a surprising fact or question",
                "key_points": ["Point 1", "Point 2", "Point 3"]
            },
            tokens_used=150
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return context.episode is not None and context.channel_profile is not None
    
    def validate_output(self, output: Dict) -> bool:
        return "idea" in output and "concept" in output


class MockResearchAgent(BaseAgent):
    """Mock agent for RESEARCH stage."""
    name = "research_agent"
    description = "Researches topics and gathers information"
    stage_type = "research"
    
    def execute(self, context: AgentContext) -> AgentResult:
        """Generate mock research output."""
        self.log_execution("Conducting research...")
        previous_idea = context.previous_outputs.get("idea", {})
        return AgentResult(
            success=True,
            output={
                "research_summary": f"Research for: {previous_idea.get('idea', 'topic')}",
                "sources": ["Source 1", "Source 2", "Source 3"],
                "key_facts": ["Fact 1", "Fact 2", "Fact 3"],
                "statistics": {"stat1": "value1", "stat2": "value2"}
            },
            tokens_used=200
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return "idea" in context.previous_outputs
    
    def validate_output(self, output: Dict) -> bool:
        return "research_summary" in output and "sources" in output


class MockScriptAgent(BaseAgent):
    """Mock agent for SCRIPT stage."""
    name = "script_agent"
    description = "Writes video scripts"
    stage_type = "script"
    
    def execute(self, context: AgentContext) -> AgentResult:
        """Generate mock script output."""
        self.log_execution("Writing script...")
        return AgentResult(
            success=True,
            output={
                "script": "Full video script content here...",
                "scenes": [
                    {"scene": 1, "description": "Intro scene", "duration": 10},
                    {"scene": 2, "description": "Main content", "duration": 60},
                    {"scene": 3, "description": "Conclusion", "duration": 15}
                ],
                "word_count": 500,
                "estimated_duration": 85
            },
            tokens_used=400
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return "research" in context.previous_outputs
    
    def validate_output(self, output: Dict) -> bool:
        return "script" in output and "scenes" in output


class MockStoryboardAgent(BaseAgent):
    """Mock agent for STORYBOARD stage."""
    name = "storyboard_agent"
    description = "Creates visual storyboards"
    stage_type = "storyboard"
    
    def execute(self, context: AgentContext) -> AgentResult:
        """Generate mock storyboard output."""
        self.log_execution("Creating storyboard...")
        return AgentResult(
            success=True,
            output={
                "storyboard_frames": [
                    {"frame": 1, "visual": "Opening shot", "text": "Title card"},
                    {"frame": 2, "visual": "Main content visual", "text": "Key point 1"},
                    {"frame": 3, "visual": "Supporting graphic", "text": "Key point 2"}
                ],
                "visual_notes": "Use bright colors and clear typography",
                "transitions": ["fade", "cut", "zoom"]
            },
            tokens_used=300
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return "script" in context.previous_outputs
    
    def validate_output(self, output: Dict) -> bool:
        return "storyboard_frames" in output


class MockAssetAgent(BaseAgent):
    """Mock agent for ASSET_GENERATION stage."""
    name = "asset_agent"
    description = "Generates visual and audio assets"
    stage_type = "asset_generation"
    
    def execute(self, context: AgentContext) -> AgentResult:
        """Generate mock asset output."""
        self.log_execution("Generating assets...")
        return AgentResult(
            success=True,
            output={
                "generated_assets": [
                    {"type": "image", "url": "/assets/image1.png", "description": "Background image"},
                    {"type": "image", "url": "/assets/image2.png", "description": "Character sprite"},
                    {"type": "audio", "url": "/assets/music.mp3", "description": "Background music"}
                ],
                "asset_count": 3,
                "total_size_mb": 15.5
            },
            tokens_used=250
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return "storyboard" in context.previous_outputs
    
    def validate_output(self, output: Dict) -> bool:
        return "generated_assets" in output


class MockVideoAgent(BaseAgent):
    """Mock agent for VIDEO_PRODUCTION stage."""
    name = "video_agent"
    description = "Assembles final video"
    stage_type = "video_production"
    
    def execute(self, context: AgentContext) -> AgentResult:
        """Generate mock video output."""
        self.log_execution("Producing video...")
        return AgentResult(
            success=True,
            output={
                "video_url": "/videos/final_video.mp4",
                "duration_seconds": 90,
                "resolution": "1920x1080",
                "format": "mp4",
                "file_size_mb": 45.2,
                "thumbnail_url": "/thumbnails/thumb1.jpg"
            },
            tokens_used=100
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return "asset_generation" in context.previous_outputs
    
    def validate_output(self, output: Dict) -> bool:
        return "video_url" in output and "duration_seconds" in output


class MockSEOAgent(BaseAgent):
    """Mock agent for SEO stage."""
    name = "seo_agent"
    description = "Optimizes content for search"
    stage_type = "seo"
    
    def execute(self, context: AgentContext) -> AgentResult:
        """Generate mock SEO output."""
        self.log_execution("Optimizing for SEO...")
        return AgentResult(
            success=True,
            output={
                "title": "Optimized Video Title",
                "description": "Compelling video description with keywords",
                "tags": ["keyword1", "keyword2", "keyword3", "trending"],
                "category": "Education",
                "seo_score": 85,
                "recommendations": ["Add more keywords", "Improve thumbnail"]
            },
            tokens_used=200
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return "video_production" in context.previous_outputs
    
    def validate_output(self, output: Dict) -> bool:
        return "title" in output and "description" in output


class MockPublishAgent(BaseAgent):
    """Mock agent for PUBLISH stage."""
    name = "publish_agent"
    description = "Handles publishing to platforms"
    stage_type = "publish"
    
    def execute(self, context: AgentContext) -> AgentResult:
        """Generate mock publish output."""
        self.log_execution("Publishing content...")
        seo_data = context.previous_outputs.get("seo", {})
        return AgentResult(
            success=True,
            output={
                "published": True,
                "platform_url": "https://youtube.com/watch?v=mock123",
                "publish_date": "2024-01-15T10:00:00Z",
                "platform_id": "mock_video_id",
                "status": "public",
                "scheduled": False
            },
            tokens_used=50
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return "seo" in context.previous_outputs
    
    def validate_output(self, output: Dict) -> bool:
        return "published" in output and "platform_url" in output


# =============================================================================
# REGISTRY INITIALIZATION
# =============================================================================

def initialize_default_registry(registry: Optional[AgentRegistry] = None) -> AgentRegistry:
    """
    Initialize the registry with default mock agents.
    
    Args:
        registry: Optional registry to initialize. Creates new if None.
        
    Returns:
        Initialized registry with all mock agents.
    """
    reg = registry or AgentRegistry()
    
    # Register all mock agents
    reg.register("idea", MockIdeaAgent())
    reg.register("research", MockResearchAgent())
    reg.register("script", MockScriptAgent())
    reg.register("storyboard", MockStoryboardAgent())
    reg.register("asset_generation", MockAssetAgent())
    reg.register("video_production", MockVideoAgent())
    reg.register("seo", MockSEOAgent())
    reg.register("publish", MockPublishAgent())
    
    return reg


# Initialize default registry with mock agents
initialize_default_registry(_default_registry)
