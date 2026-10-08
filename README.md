# Spartronics FQC Backend

FastAPI backend for the final quality-control (FQC) inspection workflow. The normal local setup uses PostgreSQL for inspection records and the backend filesystem for uploaded images. Inspection results currently come from a deterministic mock engine, not a computer-vision model.

## Current Status

Implemented:

- Create and retrieve inspections using `POST` and `GET /api/v1/inspections`.
- Upload at least three images, each paired with a unique view ID.
- Store inspection records and image references in PostgreSQL; store image bytes under `storage/images/`.
- Record a human review decision (`PASS` or `FAIL`) for a point while preserving its machine result.
- Retrieve shift inspection history with result and reviewed filters.
- Run Alembic migrations and a local PostgreSQL service through Docker Compose.

The backend test suite currently contains 37 tests. Most API tests use the in-memory repository and data-URI image adapter for isolation. The SQL repository integration test uses SQLite and temporary local-file image storage. The migration has also been applied to the local Compose PostgreSQL database, and a PostgreSQL-backed inspection/image read smoke check has succeeded; the full test suite is not currently run against PostgreSQL.

Not implemented or not production-ready:

- The inspection engine is a mock that returns four fixed points, three requiring review; it does not analyze image pixels.
- There is no health endpoint, configurable upload-size limit, image authentication, or production image-serving policy.
- Images are local files, not MinIO/S3 objects. The image route is unauthenticated and should only be used in a trusted local development environment.
- The implemented contract requires at least three paired views and uses `PASS | FAIL` review decisions. These differ from the original v0.1 requirements (`one or more` images and `PASS | DEFECT`); formal shared-contract versioning/sign-off is still needed before claiming compatibility with that version.

## Request Flow

1. A client submits inspection metadata, a JSON array of view IDs, and one image file for each view to `POST /api/v1/inspections`.
2. The API validates the view/image pairing. The image storage adapter validates each image and writes its bytes to `storage/images/` using a generated key.
3. The mock inspection engine returns point/check results. The service calculates machine and current results and builds the inspection response.
4. The SQLAlchemy repository saves the inspection and its image keys in PostgreSQL. Image bytes are not stored in PostgreSQL.
5. A reviewer can submit `PASS` or `FAIL` for a point. The latest review updates that point's current result and recalculates summaries; the machine result remains unchanged.
6. Clients can retrieve the full inspection, fetch uploaded images through the image route, or query inspections and summaries for a shift.

## Project Layout

```text
app/
  api/v1/                         HTTP routes for inspections, reviews, shifts, and images
  application/
    ports/                        Interfaces and contracts required by application workflows
    services/                     Inspection, review, and shift use-case orchestration
  domain/                         Inspection enums and result calculation rules
  infrastructure/
    persistence/                  SQLAlchemy/PostgreSQL and in-memory repositories
    storage/                      Local-file and data-URI image adapters
    vision/                        Deterministic mock inspection engine
  schemas/                         Pydantic API request and response models
migrations/                        Alembic environment and versioned schema migrations
tests/
  api/                             Inspection, review, and shift endpoint tests
  domain/                          Inspection result-rule tests
  infrastructure/                  Database repository and image-storage tests
  schemas/                         API schema and validation tests
storage/images/                    Local uploaded images; ignored by Git
docker-compose.yml                 Local PostgreSQL service
pyproject.toml                     Python package, dependencies, and pytest configuration
```

## Requirements

- Python 3.11 or newer
- Docker Desktop with Docker Compose
- Windows PowerShell for the commands below

Run all commands from the `spatronics-fqc-backend` directory. The examples use the `.venv` virtual environment. The default PostgreSQL host port is `5433` to avoid conflicting with a local PostgreSQL server on `5432`.

## Set Up and Run

Create the virtual environment and install the backend with its development/test dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Start PostgreSQL and apply the database schema:

```powershell
docker compose up -d postgres
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Open `http://127.0.0.1:8000/docs` to try the endpoints in Swagger UI. Stop the API with Ctrl+C; stop the database with `docker compose stop postgres`.

The local defaults are configured in the app and Compose file: database `fqc`, user `fqc`, development password `fqc_dev_only`, host port `5433`, and image root `storage/images/`. These credentials are for local development only. Docker Compose reads a root `.env` file for Compose settings; the Python API does not load `.env` files, so set `DATABASE_URL` or `FQC_IMAGE_STORAGE_ROOT` in the PowerShell environment before starting Uvicorn if you need to override app defaults. See `.env.example` for the variable names and local values. Do not use the development credentials in a shared or production environment.

## API Workflow

### Create an inspection

`POST /api/v1/inspections` accepts `multipart/form-data` with:

| Field | Value |
| --- | --- |
| `sku_code` | Product/SKU identifier |
| `station_id` | Inspection station identifier |
| `shift_id` | Production shift identifier |
| `view_ids` | JSON string array, for example `["top", "angle-1", "bottom"]` |
| `images` | Repeated image files, one per view ID and in matching order |

At least three unique view IDs and three valid images are required. Swagger UI may serialize `view_ids` as comma-separated text; that form is also accepted. Successful creation returns the complete inspection, including points, results, summaries, and image URLs. A missing inspection on retrieval returns HTTP 404; invalid input or image data returns HTTP 422.

### Retrieve an inspection

`GET /api/v1/inspections/{inspection_id}` returns the persisted inspection. In the default PostgreSQL mode, inspection records remain available after the API process restarts.

### Review a point

`PUT /api/v1/inspections/{inspection_id}/points/{point_id}/review` accepts JSON such as:

```json
{
  "decision": "FAIL",
  "note": "Component orientation is incorrect"
}
```

`decision` must be `PASS` or `FAIL`; `note` is optional. The latest review determines the point's current result but does not change its machine result. The response contains the updated inspection and summary.

### Read shift history

`GET /api/v1/shifts/{shift_id}/inspections` returns inspection items and a shift summary. Optional filters are `result=PASS|REVIEW|FAIL` and `reviewed=true|false`. Item filters do not reduce the overall shift summary.

### Fetch an uploaded image

Inspection responses include URLs under `/api/v1/images/...`. The backend serves uploaded image bytes from the local image directory through this route. It currently has no authentication; do not expose it outside trusted local development.

## Tests

Run the backend suite:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run only inspection API tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\api\test_inspections.py -v
```

The test suite covers API contracts and validation, review/result behavior, shift history and filters, schema validation, local image path safety, and SQLAlchemy repository round-tripping. API tests use in-memory adapters; the SQL repository integration test uses SQLite and temporary image files. PostgreSQL setup/migrations are therefore exercised separately from the routine test suite.

## Database Migrations

Apply all migrations after starting PostgreSQL:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The current initial schema revision is `20261005_0001`. To inspect the applied revision:

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

Create a new migration after changing SQLAlchemy models:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe schema change"
```

Review generated migrations before applying them. Do not edit the database schema manually as a substitute for a migration.