"""
Agent Runtime Implementation

Runtime execution environment for AI agents.
Handles agent loading, validation, execution, and result tracking.
"""

import logging
import time
from typing import Any, Dict, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

# Import from existing agents module
import sys
sys.path.insert(0, '/workspace')

from agents.base import BaseAgent, AgentContext as BaseAgentContext, AgentResult as BaseAgentResult


@dataclass
class ExecutionMetrics:
    """Execution metrics for agent runtime."""
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time_seconds: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    memory_usage_mb: float = 0.0
    success: bool = False
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time_seconds": self.execution_time_seconds,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "memory_usage_mb": self.memory_usage_mb,
            "success": self.success,
            "error_message": self.error_message
        }


@dataclass
class AgentResult:
    """
    Standardized agent execution result.
    
    Schema:
    {
        status: str,          # success, failed, timeout
        output: dict,         # Agent output data
        metadata: dict,       # Additional metadata
        execution_time: float, # Execution time in seconds
        token_usage: int,     # Tokens consumed
        error: str | null     # Error message if failed
    }
    """
    
    status: str  # success, failed, timeout
    output: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    token_usage: int = 0
    error: Optional[str] = None
    
    @classmethod
    def success(
        cls,
        output: Dict[str, Any],
        execution_time: float = 0.0,
        token_usage: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "AgentResult":
        return cls(
            status="success",
            output=output,
            execution_time=execution_time,
            token_usage=token_usage,
            metadata=metadata or {}
        )
    
    @classmethod
    def failure(
        cls,
        error: str,
        execution_time: float = 0.0,
        output: Optional[Dict[str, Any]] = None
    ) -> "AgentResult":
        return cls(
            status="failed",
            output=output or {},
            error=error,
            execution_time=execution_time
        )
    
    @classmethod
    def timeout(
        cls,
        timeout_seconds: float,
        output: Optional[Dict[str, Any]] = None
    ) -> "AgentResult":
        return cls(
            status="timeout",
            output=output or {},
            error=f"Agent execution timed out after {timeout_seconds}s"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching standard schema."""
        return {
            "status": self.status,
            "output": self.output,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "token_usage": self.token_usage,
            "error": self.error
        }


@dataclass
class RuntimeContext:
    """
    Context for agent runtime execution.
    
    Contains all information needed for agent execution including:
    - episode: The episode being processed
    - channel_profile: Channel identity and brand guidelines
    - organization_id: Tenant ID for isolation
    - previous_outputs: Results from completed stages
    - settings: Configuration options
    """
    
    episode: Any  # Episode model instance
    channel_profile: Any  # ChannelProfile model instance
    organization_id: int
    previous_outputs: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    content_job_id: Optional[int] = None
    agent_execution_id: Optional[int] = None
    
    def to_agent_context(self) -> BaseAgentContext:
        """Convert to BaseAgentContext for agent execution."""
        return BaseAgentContext(
            episode=self.episode,
            channel_profile=self.channel_profile,
            organization_id=self.organization_id,
            previous_outputs=self.previous_outputs,
            settings=self.settings
        )


class AgentRuntime:
    """
    Agent Runtime for executing AI agents.
    
    Responsibilities:
    - Load agent from registry
    - Validate input
    - Execute agent
    - Validate output
    - Measure execution time
    - Track token usage
    - Store execution result
    - Handle exceptions
    """
    
    def __init__(
        self,
        db_session: Session,
        agent_registry: Optional[Any] = None,
        default_timeout: float = 300.0  # 5 minutes
    ):
        self.db = db_session
        self.agent_registry = agent_registry
        self.default_timeout = default_timeout
        self.logger = logging.getLogger("agents.runtime")
        
        # Import registry if not provided
        if not agent_registry:
            from agents.registry import AgentRegistry
            self.agent_registry = AgentRegistry()
    
    def load_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Load an agent from the registry.
        
        Args:
            agent_name: Name of the agent to load.
            
        Returns:
            Agent instance or None if not found.
        """
        agent = self.agent_registry.get_agent(agent_name)
        if agent:
            self.logger.debug(f"Loaded agent: {agent_name}")
        else:
            self.logger.warning(f"Agent not found: {agent_name}")
        return agent
    
    def validate_input(self, agent: BaseAgent, context: RuntimeContext) -> bool:
        """
        Validate input before agent execution.
        
        Args:
            agent: Agent instance to validate against.
            context: Runtime context.
            
        Returns:
            True if valid, False otherwise.
        """
        try:
            agent_context = context.to_agent_context()
            is_valid = agent.validate_input(agent_context)
            if not is_valid:
                self.logger.warning(f"Input validation failed for agent: {agent.name}")
            return is_valid
        except Exception as e:
            self.logger.error(f"Input validation error: {e}")
            return False
    
    def validate_output(self, agent: BaseAgent, output: Dict[str, Any]) -> bool:
        """
        Validate agent output after execution.
        
        Args:
            agent: Agent instance.
            output: Output data to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        try:
            is_valid = agent.validate_output(output)
            if not is_valid:
                self.logger.warning(f"Output validation failed for agent: {agent.name}")
            return is_valid
        except Exception as e:
            self.logger.error(f"Output validation error: {e}")
            return False
    
    def execute(
        self,
        agent_name: str,
        context: RuntimeContext,
        timeout: Optional[float] = None
    ) -> AgentResult:
        """
        Execute an agent with full runtime support.
        
        Args:
            agent_name: Name of the agent to execute.
            context: Runtime context with episode and settings.
            timeout: Optional timeout override.
            
        Returns:
            AgentResult with standardized schema.
        """
        timeout = timeout or self.default_timeout
        metrics = ExecutionMetrics()
        metrics.start_time = datetime.now(timezone.utc)
        
        try:
            # Load agent
            agent = self.load_agent(agent_name)
            if not agent:
                metrics.end_time = datetime.now(timezone.utc)
                metrics.execution_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
                metrics.error_message = f"Agent not found: {agent_name}"
                return AgentResult.failure(
                    error=metrics.error_message,
                    execution_time=metrics.execution_time_seconds
                )
            
            # Validate input
            if not self.validate_input(agent, context):
                metrics.end_time = datetime.now(timezone.utc)
                metrics.execution_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
                metrics.error_message = "Input validation failed"
                return AgentResult.failure(
                    error=metrics.error_message,
                    execution_time=metrics.execution_time_seconds
                )
            
            # Convert context for agent
            agent_context = context.to_agent_context()
            
            # Execute agent with timeout (simple implementation)
            start_exec = time.time()
            try:
                # Set alarm for timeout (Unix only)
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Agent execution exceeded {timeout}s timeout")
                
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout))
                
                try:
                    result = agent.execute(agent_context)
                finally:
                    signal.alarm(0)  # Cancel alarm
                    signal.signal(signal.SIGALRM, old_handler)
                    
            except (ImportError, AttributeError):
                # Windows or signal not available, execute without timeout
                result = agent.execute(agent_context)
            
            exec_time = time.time() - start_exec
            
            # Validate output
            if not self.validate_output(agent, result.output):
                metrics.end_time = datetime.now(timezone.utc)
                metrics.execution_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
                metrics.error_message = "Output validation failed"
                return AgentResult.failure(
                    error=metrics.error_message,
                    execution_time=metrics.execution_time_seconds
                )
            
            # Build successful result
            metrics.end_time = datetime.now(timezone.utc)
            metrics.execution_time_seconds = exec_time
            metrics.tokens_used = getattr(result, 'tokens_used', 0)
            metrics.success = result.success
            
            return AgentResult.success(
                output=result.output,
                execution_time=metrics.execution_time_seconds,
                token_usage=metrics.tokens_used,
                metadata={
                    "agent_name": agent.name,
                    "agent_version": getattr(agent, 'version', None),
                    "stage_type": getattr(agent, 'stage_type', None)
                }
            )
            
        except TimeoutError as e:
            metrics.end_time = datetime.now(timezone.utc)
            metrics.execution_time_seconds = timeout
            metrics.error_message = str(e)
            self.logger.error(f"Agent timeout: {agent_name} - {e}")
            return AgentResult.timeout(timeout_seconds=timeout)
            
        except Exception as e:
            metrics.end_time = datetime.now(timezone.utc)
            metrics.execution_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.error_message = str(e)
            self.logger.exception(f"Agent execution failed: {agent_name} - {e}")
            return AgentResult.failure(
                error=str(e),
                execution_time=metrics.execution_time_seconds
            )
    
    def execute_and_store(
        self,
        agent_name: str,
        context: RuntimeContext,
        agent_execution_id: int,
        timeout: Optional[float] = None
    ) -> AgentResult:
        """
        Execute an agent and store the result in the database.
        
        Args:
            agent_name: Name of the agent to execute.
            context: Runtime context.
            agent_execution_id: ID of the AgentExecution record.
            timeout: Optional timeout override.
            
        Returns:
            AgentResult with execution outcome.
        """
        from database.models import AgentExecution, AgentExecutionStatus
        
        # Execute the agent
        result = self.execute(agent_name, context, timeout)
        
        # Update AgentExecution record
        agent_exec = self.db.query(AgentExecution).filter(
            AgentExecution.id == agent_execution_id
        ).first()
        
        if agent_exec:
            if result.status == "success":
                agent_exec.status = AgentExecutionStatus.SUCCESS
            elif result.status == "timeout":
                agent_exec.status = AgentExecutionStatus.TIMEOUT
            else:
                agent_exec.status = AgentExecutionStatus.FAILED
            
            agent_exec.output_data = result.output
            agent_exec.error_message = result.error
            agent_exec.duration_seconds = result.execution_time
            agent_exec.total_tokens = result.token_usage
            agent_exec.completed_at = datetime.now(timezone.utc)
            
            # Store metadata
            agent_exec.extra_data = {
                **(agent_exec.extra_data or {}),
                **result.metadata
            }
            
            self.db.commit()
            self.logger.info(
                f"Stored agent execution result: {agent_execution_id} - {result.status}"
            )
        
        return result
