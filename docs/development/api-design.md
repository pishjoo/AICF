# AICF v2 API Design

## Overview

This document defines the RESTful API design for AICF v2.

**Note**: API endpoints are planned (Phase 5); current implementation is code-only.

---

## Authentication Endpoints

### POST /auth/register

Register a new organization and owner user.

**Request:**
```json
{
  "organization_name": "My Company",
  "organization_slug": "my-company",
  "email": "owner@example.com",
  "password": "securePassword123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "organization": {
    "id": 1,
    "name": "My Company",
    "slug": "my-company"
  },
  "user": {
    "id": 1,
    "email": "owner@example.com",
    "roles": ["owner"]
  }
}
```

### POST /auth/login

Authenticate user and obtain tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response:** Same as register.

### POST /auth/refresh

Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## Channel Endpoints

### GET /channels

List all channels for current organization.

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Tech Reviews",
      "description": "Technology product reviews",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "pages": 1
}
```

### POST /channels

Create a new channel profile.

**Request:**
```json
{
  "name": "Tech Reviews",
  "description": "Technology product reviews and tutorials",
  "target_audience": {
    "age_range": [25, 45],
    "interests": ["technology", "gadgets"]
  },
  "brand_guidelines": {
    "colors": {"primary": "#0066CC"},
    "tone_of_voice": "professional yet approachable"
  }
}
```

### GET /channels/{channel_id}

Get channel details.

**Response:**
```json
{
  "id": 1,
  "name": "Tech Reviews",
  "description": "...",
  "target_audience": {...},
  "brand_guidelines": {...},
  "content_strategy": {...},
  "playlists": [...]
}
```

---

## Playlist Endpoints

### GET /channels/{channel_id}/playlists

List playlists for a channel.

### POST /channels/{channel_id}/playlists

Create a new playlist.

**Request:**
```json
{
  "title": "Q1 2024 Content",
  "description": "First quarter content plan",
  "playlist_type": "planned"
}
```

---

## Episode Endpoints

### GET /playlists/{playlist_id}/episodes

List episodes in a playlist.

### POST /playlists/{playlist_id}/episodes

Create a new episode.

**Request:**
```json
{
  "title": "iPhone 16 Review",
  "topic": "Latest Apple smartphone review",
  "description": "Comprehensive review of iPhone 16 features"
}
```

### GET /episodes/{episode_id}

Get episode details with workflow status.

**Response:**
```json
{
  "id": 1,
  "title": "iPhone 16 Review",
  "status": "scripting",
  "workflow_status": {
    "overall": "running",
    "completed_stages": 2,
    "total_stages": 8,
    "current_stage": "script"
  }
}
```

---

## Workflow Endpoints

### POST /episodes/{episode_id}/workflow

Start workflow for an episode.

**Response:**
```json
{
  "workflow_id": 1,
  "episode_id": 1,
  "status": "pending",
  "stages_created": 8
}
```

### GET /episodes/{episode_id}/workflow/status

Get workflow execution status.

**Response:**
```json
{
  "episode_id": 1,
  "overall_status": "running",
  "progress": "2/8",
  "stages": [
    {
      "stage_type": "idea",
      "status": "completed",
      "completed_at": "2024-01-15T10:00:05Z"
    },
    {
      "stage_type": "research",
      "status": "completed",
      "completed_at": "2024-01-15T10:00:15Z"
    },
    {
      "stage_type": "script",
      "status": "running",
      "started_at": "2024-01-15T10:00:16Z"
    }
  ]
}
```

### POST /episodes/{episode_id}/workflow/pause

Pause workflow execution.

### POST /episodes/{episode_id}/workflow/resume

Resume paused workflow.

### POST /episodes/{episode_id}/workflow/stages/{stage_type}/retry

Retry a failed stage.

---

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "title",
      "reason": "required field missing"
    },
    "trace_id": "abc123-def456"
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Planned (Phase 5)
