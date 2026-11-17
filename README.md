# Simple Image Search

A production-ready application for batch image search and download via Google Custom Search API.

## Features

- Batch import of product names (one per line)
- Automatic image search via Google Custom Search
- Concurrent image download with retry logic
- Real-time progress tracking
- Gallery and table view modes
- Search-provider thumbnails with cached backend previews and fallback sources
- File deduplication by hash
- SSRF protection

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Backend     │────▶│    PostgreSQL   │
│  (React + Vite) │     │   (FastAPI)     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Google Custom  │
                        │   Search API    │
                        └─────────────────┘
```

### Key Design Decisions

1. **SearchProvider Interface** - Abstraction layer for search providers, allowing easy replacement
2. **StorageProvider Interface** - Abstraction for file storage (local/S3)
3. **BackgroundTasks** - Simple async processing for MVP (migratable to Celery)
4. **Polling** - Frontend polls for status updates (5s interval)

### Image previews

Search results keep original and thumbnail URLs separately. The browser tries the
provider thumbnail first, then `/api/images/{image_id}/preview/{index}`, then the
original URL. Existing batches without thumbnail URLs use the same preview endpoint
without a database migration. Original download links still point to full-size files.

The backend validates each remote destination and redirect, limits response size,
checks image bytes, and caches PNG previews up to 512×512 under
`STORAGE_PATH/previews`. Concurrent requests for the same preview share one download.
Cached previews are generated data; they can be removed when the application is
stopped and are recreated on demand. An unavailable source shows a placeholder.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Google Custom Search API key and Search Engine ID (CX)

### Setup

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd SimpleImageSearch
   ```

2. Create `.env` file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your Google API credentials:
   ```
   GOOGLE_API_KEY=your_api_key_here
   GOOGLE_CSE_CX=your_search_engine_id_here
   ```

4. Start the application:
   ```bash
   docker-compose up -d
   ```

5. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Local Development (without Docker)

1. Start PostgreSQL:
   ```bash
   docker run -d --name postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=imagesearch -p 5432:5432 postgres:15-alpine
   ```

2. Backend:
   ```bash
   cd apps/backend
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   
   # Run migrations
   alembic upgrade head
   
   # Start server
   uvicorn src.main:app --reload
   ```

3. Frontend:
   ```bash
   cd apps/frontend
   npm install
   npm run dev
   ```

## Project Structure

```
SimpleImageSearch/
├── apps/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── api/          # REST API routes
│   │   │   ├── application/  # Business logic services
│   │   │   ├── domain/       # Entities, value objects, interfaces
│   │   │   ├── infrastructure/ # DB, providers, config
│   │   │   └── main.py
│   │   └── tests/
│   └── frontend/
│       ├── src/
│       │   ├── api/          # API client
│       │   ├── components/   # React components
│       │   ├── hooks/        # React hooks
│       │   ├── pages/        # Page components
│       │   ├── stores/       # Zustand stores
│       │   └── types/        # TypeScript types
│       └── package.json
├── data/images/              # Uploaded images storage
├── docker-compose.yml
└── .env.example
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/batches` | Create batch from lines |
| GET | `/api/batches` | List batches |
| GET | `/api/batches/{id}` | Get batch details |
| GET | `/api/batches/{id}/items` | Get batch items |
| GET | `/api/batches/{id}/stats` | Get processing stats |
| DELETE | `/api/batches/{id}` | Delete batch |
| POST | `/api/items/{id}/retry` | Retry failed item |
| POST | `/api/items/{id}/approve` | Approve item |
| GET | `/api/images/{id}/file` | Serve image file |
| GET | `/api/images/item/{id}/file` | Serve image by item ID |
| GET | `/api/health` | Health check |

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `GOOGLE_API_KEY` | Google API key | Required |
| `GOOGLE_CSE_CX` | Custom Search Engine ID | Required |
| `STORAGE_PATH` | Local storage path | `/data/images` |
| `MAX_FILE_SIZE_MB` | Max image size in MB | `10` |
| `DOWNLOAD_TIMEOUT` | HTTP timeout in seconds | `30` |
| `MAX_CONCURRENT_DOWNLOADS` | Concurrent download limit | `5` |
| `MAX_RETRIES` | Max retry attempts | `3` |

## TODO (for Production)

- [ ] Add authentication (JWT/API keys)
- [ ] Implement SSE for real-time updates
- [ ] Add S3-compatible storage
- [ ] Implement Celery for job queue
- [ ] Add Prometheus metrics
- [ ] Write unit and integration tests
- [ ] Add CI/CD pipeline
- [ ] Implement manual image selection from multiple results
- [ ] Add CSV export functionality
- [ ] Add OpenCart integration
- [ ] Add batch retry for failed items
- [ ] Implement file deduplication index

## License

MIT
