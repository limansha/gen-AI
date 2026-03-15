# AIFSD Backend API

FastAPI backend for AIFSD App with Google OAuth authentication.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the `backend` directory:
```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
JWT_SECRET_KEY=your_strong_secret_key_min_32_bytes
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080
JWT_REFRESH_TOKEN_EXPIRE_MINUTES=43200
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
CORS_ORIGINS=http://localhost:8081,exp://localhost:8081
# Note: http://localhost:8081 is required for Expo dev server OAuth callback at /api/auth/callback
```

## API Endpoints

### Authentication

- `POST /auth/google/callback` - Exchange Google OAuth code for JWT token
  - Request body: `{ "code": "...", "redirect_uri": "..." }`
  - Response: `{ "access_token": "...", "token_type": "bearer" }`

### User

- `GET /api/user` - Get current user information (requires JWT)
  - Headers: `Authorization: Bearer <token>`
  - Response: `{ "id": "...", "email": "...", "name": "..." }`

### Journey

- `POST /api/journey/actions` - Get actions/tasks for a journey (requires JWT)
  - Headers: `Authorization: Bearer <token>`
  - Request body: `{ "journeySummary": "I want to become more confident in public speaking..." }`
  - Response: `{ "actions": [{ "title": "...", "duration": "...", "steps": [...], "order": 1 }, ...] }`

### Health Check

- `GET /health` - Health check endpoint

## Architecture

The backend follows Domain-Driven Design (DDD) principles:

- **Presentation Layer** (`src/presentation/`): API routes, middleware, dependencies
- **Application Layer** (`src/application/`): Use cases and business logic
  - **Journey Workflow**: LangGraph-based workflow for journey processing
  - **Agents**: LLM-powered agents for guardrails, matching, understanding, and generation
- **Domain Layer** (`src/domain/`): Core entities and value objects
- **Infrastructure Layer** (`src/infrastructure/`): Database, external services (LLM clients)

## Journey Processing Workflow

The journey actions endpoint uses a LangGraph workflow that:

1. **Guardrails**: Validates and sanitizes input using LLM and rule-based checks
2. **Database Check**: Uses LLM to extract traits and match against existing journeys
3. **Understanding** (if new): Extracts user intent and needs
4. **Generation** (if new): Generates actions and traits using LLM
5. **Save/Retrieve**: Saves new journeys or retrieves existing ones from PostgreSQL
6. **Response**: Returns formatted list of actions

The workflow is implemented using LangGraph for state management, conditional routing, and observability.

## Security

- JWT access tokens with 7-day expiry (10080 minutes)
- JWT refresh tokens with 30-day expiry (43200 minutes)
- CORS with explicit allow-list
- Security headers (HSTS, CSP, X-Content-Type-Options)
- PII masking in logs
- Input validation with Pydantic
- SQL injection prevention via SQLAlchemy ORM

