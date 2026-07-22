# AICF v2 Business Rules

## Overview

This document defines the business rules, validation logic, and constraints enforced by AICF v2.

---

## Organization Rules

### ORG-001: Organization Creation
**Rule**: Every organization must have a unique slug and at least one owner.

**Validation:**
```python
def validate_organization_creation(data):
    if not data.name or len(data.name) < 2:
        raise ValidationError("Organization name must be at least 2 characters")
    
    if not is_slug_unique(data.slug):
        raise ValidationError("Slug already exists")
    
    if not data.owner_user_id:
        raise ValidationError("Owner must be specified")
```

### ORG-002: Subscription Plan
**Rule**: Organizations must have a valid subscription plan.

**Allowed Values:**
- `free` - Limited features
- `pro` - Full features
- `enterprise` - All features + support

---

## User & Access Rules

### USER-001: Email Uniqueness
**Rule**: Email addresses must be unique within an organization.

### USER-002: Role Assignment
**Rule**: Users can only be assigned roles that exist in the system.

### USER-003: Owner Protection
**Rule**: An organization must always have at least one owner.

**Implementation:**
```python
def remove_user_from_org(user_id, org_id):
    # Check if user is the only owner
    owners = db.query(UserRole).join(Role).filter(
        UserRole.user_id == user_id,
        UserRole.organization_id == org_id,
        Role.name == "owner"
    ).count()
    
    if owners > 0:
        remaining_owners = db.query(UserRole).join(Role).filter(
            UserRole.organization_id == org_id,
            Role.name == "owner",
            UserRole.user_id != user_id
        ).count()
        
        if remaining_owners == 0:
            raise BusinessRuleError("Cannot remove the last owner")
```

---

## Channel Profile Rules

### CHAN-001: Brand Guidelines Required
**Rule**: Every channel profile must have brand guidelines defined.

### CHAN-002: Target Audience Specification
**Rule**: Channel profiles should define target audience for better content generation.

### CHAN-003: One Strategy Per Channel
**Rule**: Each channel has exactly one content strategy.

---

## Playlist Rules

### PLAY-001: Playlist Type Validation
**Rule**: Playlists must be either PLANNED or DYNAMIC.

**Types:**
- `PLANNED`: Manually curated episodes
- `DYNAMIC`: Auto-generated from RSS/trends

### PLAY-002: Dynamic Playlist Rules
**Rule**: Dynamic playlists must have generation rules defined.

```python
if playlist.playlist_type == PlaylistType.DYNAMIC:
    if not playlist.generation_rules:
        raise ValidationError("Dynamic playlists require generation_rules")
    
    required_fields = ["source_type", "frequency", "filters"]
    for field in required_fields:
        if field not in playlist.generation_rules:
            raise ValidationError(f"Missing required field: {field}")
```

---

## Episode Rules

### EP-001: Status Transitions
**Rule**: Episodes follow a defined status lifecycle.

**Valid Transitions:**
```
PLANNED → RESEARCHING → SCRIPTING → STORYBOARDING → 
ASSET_GENERATING → VIDEO_PRODUCING → SEO_OPTIMIZED → PUBLISHED

Any status → CANCELLED (terminal state)
Any status → FAILED (recoverable via retry)
```

### EP-002: Episode Must Belong to Playlist
**Rule**: Every episode must be associated with a playlist.

### EP-003: Episode Must Reference Channel
**Rule**: Episodes must reference a channel profile for brand consistency.

---

## Workflow Rules

### WF-001: Stage Order Enforcement
**Rule**: Workflow stages must execute in defined order.

**Order:**
1. IDEA
2. RESEARCH
3. SCRIPT
4. STORYBOARD
5. ASSET_GENERATION
6. VIDEO_PRODUCTION
7. SEO
8. PUBLISH

### WF-002: Stage Dependency
**Rule**: A stage cannot start until the previous stage completes successfully.

**Implementation:**
```python
def can_start_stage(episode, stage_type):
    stage_order = WorkflowStageType.get_stage_order()
    current_index = stage_order.index(stage_type)
    
    if current_index == 0:
        return True  # First stage can always start
    
    previous_stage = stage_order[current_index - 1]
    previous_job = get_stage_job(episode, previous_stage)
    
    return previous_job.status == ContentJobStatus.COMPLETED
```

### WF-003: Retry Limit
**Rule**: Stages can be retried up to max_retries (default: 3).

### WF-004: Pause/Resume Rules
**Rule**: Only RUNNING workflows can be paused; only PAUSED workflows can be resumed.

---

## Agent Execution Rules

### AGENT-001: Input Validation
**Rule**: Agents must validate input before execution.

### AGENT-002: Output Validation
**Rule**: Agents must produce output matching their contract.

### AGENT-003: Token Tracking
**Rule**: All agent executions must track token usage for cost calculation.

### AGENT-004: Error Recording
**Rule**: Failed executions must record error messages for debugging.

---

## Asset Rules

### ASSET-001: Asset Type Validation
**Rule**: Assets must have a valid type.

**Allowed Types:**
- `image`
- `audio`
- `video`
- `graphic`
- `subtitle`
- `thumbnail`

### ASSET-002: File Size Limits
**Rule**: Assets must not exceed size limits based on subscription plan.

| Plan | Max Image | Max Video |
|------|-----------|-----------|
| Free | 5 MB | 100 MB |
| Pro | 20 MB | 500 MB |
| Enterprise | 50 MB | 2 GB |

---

## Publishing Rules

### PUB-001: Platform Validation
**Rule**: Content can only be published to supported platforms.

**Supported Platforms:**
- YouTube (planned)
- Instagram (planned)
- TikTok (planned)
- LinkedIn (planned)

### PUB-002: SEO Requirements
**Rule**: Content must have SEO metadata before publishing.

**Required Fields:**
- Title (max 100 chars)
- Description (max 5000 chars)
- Tags (min 3, max 30)
- Category

### PUB-003: Publish State
**Rule**: Once published, episode status becomes PUBLISHED (terminal).

---

## Cost Calculation Rules

### COST-001: Token-Based Pricing
**Rule**: AI costs calculated based on token usage.

```python
def calculate_cost(execution: AgentExecution) -> Decimal:
    model_pricing = {
        "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "claude-3": {"input": 0.03, "output": 0.06},
    }
    
    pricing = model_pricing.get(execution.model, pricing["gpt-3.5-turbo"])
    input_cost = (execution.prompt_tokens / 1000) * pricing["input"]
    output_cost = (execution.completion_tokens / 1000) * pricing["output"]
    
    return Decimal(input_cost + output_cost)
```

### COST-002: Episode Total Cost
**Rule**: Episode cost = sum of all agent execution costs.

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Active Development
