# Media Library UX

## 1. Purpose

### Why AICF needs Media Library

The AI Content Factory (AICF) generates a wide variety of media assets including videos, images, audio files, and other digital content. Without a centralized Media Library:

- Generated assets become scattered and difficult to locate
- Users cannot efficiently reuse existing media across projects
- There is no organized way to manage the growing library of AI-generated content
- Teams lose productivity searching for previously created assets

The Media Library provides a unified system for storing, organizing, and accessing all media assets generated through AICF pipelines.

---

## 2. User Problems

### Finding Assets

Users struggle to locate specific media files when:
- Assets are stored in disconnected locations
- There is no search or filtering capability
- File naming conventions are inconsistent
- No visual preview or metadata is available

### Organizing Generated Content

As the volume of AI-generated content grows:
- Users need logical groupings beyond flat file storage
- Different projects require different organizational structures
- Some assets should be grouped by campaign, others by project type
- Archived content needs to be separated from active work

### Reusing Media Files

Without proper organization:
- Users recreate content that already exists
- Brand consistency suffers when approved assets cannot be found
- Time is wasted regenerating similar content
- Valuable AI-generated assets become lost or forgotten

---

## 3. Collection Concept

### What is a Collection?

A **Collection** is a logical grouping of media assets that share a common purpose, theme, or context. Collections provide:

- **Organization**: Group related assets together for easy access
- **Context**: Understand why assets were created and how they relate
- **Reusability**: Quickly find sets of assets for new projects
- **Management**: Apply actions to groups of assets at once

### Why Collections Exist

Collections solve the fundamental problem of scale. As users generate hundreds or thousands of media assets:

1. **Flat lists become unmanageable** - Scrolling through all assets is inefficient
2. **Projects need context** - Assets gain meaning when grouped by purpose
3. **Workflows require structure** - Teams need to organize assets by campaign, client, or project phase
4. **Archiving needs boundaries** - Old projects should be separable from active work

### Relationship Between Collections and Media Assets

```
┌─────────────────────┐
│   MediaCollection   │
│  ─────────────────  │
│  - id               │
│  - name             │
│  - description      │
│  - type             │
│  - status           │
│  - assetCount       │
└──────────┬──────────┘
           │
           │ contains
           ▼
┌─────────────────────┐
│    MediaAsset       │
│  ─────────────────  │
│  - id               │
│  - file             │
│  - metadata         │
│  - ...              │
└─────────────────────┘
```

- A **MediaCollection** contains zero or more **MediaAssets**
- A **MediaAsset** can belong to multiple collections (many-to-many relationship)
- Collections provide the organizational layer; assets provide the actual content

### Collection Types

| Type | Purpose | Example |
|------|---------|---------|
| `project` | Assets for a specific content project | "YouTube Episode 5 Assets" |
| `campaign` | Assets for a marketing campaign | "Q1 Product Launch" |
| `personal` | Personal workspace collections | "AI Experiments" |
| `archive` | Archived/historical collections | "2023 Campaigns" |

### Collection Status

| Status | Meaning |
|--------|---------|
| `active` | Collection is in active use |
| `archived` | Collection is archived (read-only) |

---

## 4. User Flow

### Typical Workflow

```
User uploads media
       ↓
Asset appears in Media Library (unassigned)
       ↓
User creates or selects a Collection
       ↓
User assigns asset to Collection
       ↓
Collection becomes reusable for Content Factory projects
       ↓
Future projects can browse and reuse collection assets
```

### Detailed Steps

1. **Upload Phase**
   - User uploads media through the Media Upload UI
   - Asset is stored with metadata (file type, size, creation date, etc.)
   - Asset initially appears in "Unassigned" or "Recent" view

2. **Organization Phase**
   - User browses existing collections or creates a new one
   - User selects one or more assets
   - User assigns assets to the appropriate collection

3. **Utilization Phase**
   - When starting a new Content Factory project
   - User browses collections to find relevant assets
   - User selects assets from collections to include in the project
   - Project inherits or references collection assets

4. **Maintenance Phase**
   - User periodically reviews collections
   - Outdated collections can be archived
   - Assets can be moved between collections as needed

---

## 5. Future Backend Requirements

This section describes potential API endpoints that may be needed in future phases. **No implementation is required at this stage.**

### Collection Management APIs

#### Create Collection
```
POST /api/collections
Body: {
  name: string,
  description?: string,
  type: 'project' | 'campaign' | 'personal' | 'archive',
  status?: 'active' | 'archived'
}
Response: MediaCollection
```

#### Get Collections
```
GET /api/collections
Query params: ?type=project&status=active&page=1&limit=20
Response: { collections: MediaCollection[], total: number }
```

#### Get Collection by ID
```
GET /api/collections/:id
Response: MediaCollection
```

#### Update Collection
```
PATCH /api/collections/:id
Body: { name?, description?, status? }
Response: MediaCollection
```

#### Delete Collection
```
DELETE /api/collections/:id
Response: { success: boolean }
```

### Asset-Collection Relationship APIs

#### Add Asset to Collection
```
POST /api/collections/:id/assets
Body: { assetId: string }
Response: { success: boolean }
```

#### Remove Asset from Collection
```
DELETE /api/collections/:id/assets/:assetId
Response: { success: boolean }
```

#### Get Collection Assets
```
GET /api/collections/:id/assets
Query params: ?page=1&limit=50
Response: { assets: MediaAsset[], total: number }
```

### Search & Discovery APIs

#### Search Collections
```
GET /api/collections/search?q=query&type=campaign
Response: { collections: MediaCollection[], total: number }
```

#### Find Collections by Asset
```
GET /api/assets/:id/collections
Response: { collections: MediaCollection[] }
```

### Bulk Operations

#### Bulk Add Assets to Collection
```
POST /api/collections/:id/assets/bulk
Body: { assetIds: string[] }
Response: { added: number, failed: number }
```

#### Move Assets Between Collections
```
POST /api/assets/move
Body: { assetIds: string[], fromCollectionId?: string, toCollectionId: string }
Response: { moved: number, failed: number }
```

---

## Notes for Future Implementation

- Collections should support pagination for large asset lists
- Consider implementing soft-delete for collections (archival vs permanent deletion)
- Asset-count should be maintained efficiently (cached or computed)
- Permissions may be needed for shared/team collections in future SaaS features
- Tags or labels could complement collections for cross-cutting organization
