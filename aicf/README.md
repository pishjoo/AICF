# AICF - AI Content Factory

A multi-agent AI system for automated YouTube content production.

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- pip or uv

### Installation

1. **Clone and navigate to project:**
```bash
cd aicf
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**

Create a `.env` file in the project root:
```env
# Database
DATABASE_URL=postgresql://aicf:aicf_password@localhost:5432/aicf_db

# AI Provider (choose one)
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here

# Or use Anthropic
# AI_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Or use local Ollama
# AI_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434

# Application
DEBUG=true
ENVIRONMENT=development
```

5. **Start PostgreSQL:**

Make sure PostgreSQL is running and create the database:
```bash
createdb aicf_db
```

6. **Run the backend:**
```bash
cd aicf
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

7. **Run the dashboard (in another terminal):**
```bash
cd aicf
streamlit run app/dashboard/app.py
```

8. **Access the application:**
- API Docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

## Project Structure

```
aicf/
├── app/
│   ├── api/
│   │   ├── routes.py      # API endpoints
│   │   └── schemas.py     # Pydantic models
│   ├── dashboard/
│   │   └── app.py         # Streamlit dashboard
│   └── main.py            # FastAPI application
├── agents/
│   ├── base.py            # Base agent class
│   └── ...                # Specialized agents (to be implemented)
├── core/
│   ├── ai_provider.py     # AI provider abstraction
│   ├── config.py          # Configuration management
│   └── workflow.py        # Workflow engine
├── database/
│   ├── connection.py      # Database connection
│   └── models.py          # SQLAlchemy models
├── profiles/              # Content profile storage
├── projects/              # Project files storage
├── storage/               # General storage
└── tests/                 # Test suite
```

## Features

### Content Profiles
Define YouTube channel identities with:
- Channel name, niche, target audience
- Visual style and branding rules
- Forbidden elements and constraints
- Recurring characters
- Music style preferences
- Video format and duration rules

### Multi-Agent System (Planned)
- **Research Agent**: Gathers information and trends
- **Idea Generator**: Creates video concepts
- **Script Writer**: Writes engaging scripts
- **Storyboard Agent**: Plans visual sequences
- **Image Prompt Agent**: Generates image prompts
- **Video Production Agent**: Manages video creation
- **SEO Agent**: Optimizes titles, descriptions, tags
- **QC Agent**: Quality control and brand compliance

### Workflow Engine
Automated pipeline: Idea → Research → Script → Storyboard → Assets → Video → SEO → Publish

## API Endpoints

### Profiles
- `GET /api/v1/profiles` - List all profiles
- `POST /api/v1/profiles` - Create profile
- `GET /api/v1/profiles/{id}` - Get profile
- `PUT /api/v1/profiles/{id}` - Update profile
- `DELETE /api/v1/profiles/{id}` - Delete profile

### Projects
- `GET /api/v1/projects` - List all projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Workflow
- `GET /api/v1/projects/{id}/workflow` - Get workflow status
- `POST /api/v1/projects/{id}/workflow/execute` - Execute workflow

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
# Install dev dependencies
pip install black flake8 mypy

# Format code
black .

# Lint
flake8 .

# Type check
mypy .
```

## Architecture Decisions

- **Backend**: FastAPI for async performance and automatic OpenAPI docs
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Providers**: Abstracted interface supporting OpenAI, Anthropic, Ollama
- **Frontend**: Streamlit for rapid dashboard development
- **Agents**: Modular design with base class for consistency

## Next Steps (Phase 1)

1. ✅ Configuration system
2. ✅ Database connection
3. ✅ Base Agent class
4. ✅ AI Provider abstraction
5. ✅ Workflow engine skeleton
6. ✅ Content Profile model
7. ✅ Basic API endpoints
8. ✅ Basic Streamlit dashboard

**Next Phase**: Implement specialized agents (Research, Idea, Script, etc.)

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
