# Repository Guidelines

## Project Structure & Module Organization

This repository is a Dockerized monorepo for batch image search and download. The backend lives in `apps/backend` and uses FastAPI with a layered structure: `src/api` for routes, `src/application` for services and DTOs, `src/domain` for entities and interfaces, and `src/infrastructure` for database, configuration, and providers. The frontend lives in `apps/frontend` and uses React, Vite, TypeScript, React Query, MUI, and Zustand. Frontend code is organized under `src/api`, `src/components`, `src/hooks`, `src/pages`, `src/stores`, and `src/types`. Downloaded image data is persisted under `data/images`; keep generated files out of commits.

## Build, Test, and Development Commands

Run the full stack with Docker:

```bash
docker-compose up -d
```

Backend local workflow:

```bash
cd apps/backend
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload
pytest
```

Frontend local workflow:

```bash
cd apps/frontend
npm install
npm run dev
npm run build
npm run lint
```

`npm run dev` starts Vite, `npm run build` type-checks and builds production assets, and `npm run lint` runs ESLint.

## Coding Style & Naming Conventions

Use Python 3.11+ for backend code. Keep async database and HTTP code explicit, and follow existing module boundaries. Use `snake_case` for Python modules, functions, and variables; use `PascalCase` for classes and domain entities.

Use strict TypeScript in the frontend. React components should use `PascalCase` file and export names, hooks should start with `use`, and API helpers should stay in `src/api`. Prefer the configured `@/*` import alias for frontend source imports.

## Testing Guidelines

Backend pytest settings are in `apps/backend/pyproject.toml`: tests belong in `apps/backend/tests`, files should be named `test_*.py`, classes `Test*`, and functions `test_*`. Use `pytest --cov=src` when touching shared backend behavior. There is currently no frontend test setup; at minimum run `npm run build` and `npm run lint` for frontend changes.

## Commit & Pull Request Guidelines

The current history uses short, imperative commit subjects such as `Init` and `UI upd`. Keep subjects concise and action-oriented, for example `Add batch retry endpoint`. Pull requests should include a brief summary, verification commands run, linked issues when relevant, and screenshots for UI changes.

## Security & Configuration Tips

Copy `.env.example` to `.env` for local work and never commit real API keys. Search providers are configured with `SEARCH_PROVIDER` plus keys such as `BRAVE_API_KEY`, `SERPAPI_API_KEY`, or `GOOGLE_API_KEY`. Preserve SSRF protections and domain allow/block settings when changing downloader or provider code.
