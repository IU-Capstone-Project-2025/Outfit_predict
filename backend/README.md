

## Backend Overview


* **FastAPI** — for building the asynchronous API
* **PostgreSQL** — to store metadata about images
* **MinIO** — for S3-compatible object storage
* **Docker Compose** — to run everything together in containers

### Key Endpoints

| Endpoint                   | Method | Description                                 |
| -------------------------- | ------ | ------------------------------------------- |
| `/api/v1/images/`          | GET    | Get list of all uploaded images (paginated) |
| `/api/v1/images/`          | POST   | Upload a new image with description         |
| `/api/v1/images/{id}`      | GET    | Get image metadata                          |
| `/api/v1/images/{id}/file` | GET    | Proxy image file download from MinIO        |

Responses contain full metadata and a downloadable URL for each image.

---

## Directory layout

```
proj/
├── docker-compose.yml
├── .env.example
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── __init__.py
        ├── main.py
        ├── deps.py
        ├── core/
        │   ├── __init__.py
        │   └── config.py
        ├── db/
        │   ├── __init__.py
        │   └── database.py
        ├── models/
        │   ├── __init__.py
        │   └── image.py
        ├── schemas/
        │   ├── __init__.py
        │   └── image.py
        ├── crud/
        │   ├── __init__.py
        │   └── image.py
        ├── storage/
        │   ├── __init__.py
        │   └── minio_client.py
        └── api/
            ├── __init__.py
            └── v1/
                ├── __init__.py
                └── endpoints/
                    ├── __init__.py
                    └── image.py
```

---

## How to Run with Docker Compose

```bash
# 1. Copy environment configuration
cp .env.example .env

# 2. Build and run all containers
docker compose up --build

# 3. Open FastAPI docs
#    http://localhost:8000/docs

# 4. MinIO Console UI (optional)
#    http://localhost:9001
```

---

## Example Usage

```bash
# Upload image
curl -X POST "http://localhost:8000/api/v1/images/" \
     -F "description=Sunset in Berlin" \
     -F "file=@sunset.jpg"

# List all images
curl http://localhost:8000/api/v1/images/

# Download specific image
curl http://localhost:8000/api/v1/images/<id>/file --output downloaded.jpg
```

---

## How It Works Internally

1. **Upload:** file sent via `POST /images/`, streamed into MinIO.
2. **DB Save:** metadata (`description`, `object_name`, etc.) stored in PostgreSQL.
3. **Download:** image is served via proxy endpoint (`/images/{id}/file`) so direct access to MinIO is hidden.
4. **List/Read:** metadata and download URL are returned from listing and detail endpoints.

> This avoids exposing raw S3 links and allows full control over delivery.

---

## Notes

* Replace in-code table creation with Alembic migrations for production use
* Use authentication and access control if serving private content
* You can switch to real S3 or compatible services like Wasabi, DigitalOcean Spaces, etc.
