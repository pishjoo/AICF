"""
Workflow Exceptions

Custom exceptions for workflow engine operations.
"""


class WorkflowError(Exception):
    """Base exception for workflow-related errors."""
    
    def __init__(self, message: str, workflow_id: int = None):
        self.message = message
        self.workflow_id = workflow_id
        super().__init__(self.message)


class StageExecutionError(WorkflowError):
    """Exception raised when a stage execution fails."""
    
    def __init__(self, message: str, stage_type: str, workflow_id: int = None):
        self.stage_type = stage_type
        super().__init__(message, workflow_id)


class StageNotFoundError(WorkflowError):
    """Exception raised when a stage is not found."""
    
    def __init__(self, stage_type: str, workflow_id: int = None):
        self.stage_type = stage_type
        message = f"Stage '{stage_type}' not found"
        if workflow_id:
            message += f" in workflow {workflow_id}"
        super().__init__(message, workflow_id)


class WorkflowNotPausedError(WorkflowError):
    """Exception raised when trying to resume a workflow that is not paused."""
    
    def __init__(self, workflow_id: int = None):
        message = "Workflow is not paused"
        super().__init__(message, workflow_id)


class InvalidStageTransitionError(WorkflowError):
    """Exception raised when an invalid stage transition is attempted."""
    
    def __init__(self, from_stage: str, to_stage: str, workflow_id: int = None):
        self.from_stage = from_stage
        self.to_stage = to_stage
        message = f"Invalid stage transition from '{from_stage}' to '{to_stage}'"
        super().__init__(message, workflow_id)


class AgentExecutionError(WorkflowError):
    """Exception raised when an agent execution fails."""
    
    def __init__(self, message: str, agent_name: str, stage_type: str):
        self.agent_name = agent_name
        self.stage_type = stage_type
        super().__init__(f"Agent '{agent_name}' failed at stage '{stage_type}': {message}")


class WorkflowValidationError(WorkflowError):
    """Exception raised when workflow validation fails."""
    
    def __init__(self, message: str, validation_errors: list = None):
        self.validation_errors = validation_errors or []
        super().__init__(message)
