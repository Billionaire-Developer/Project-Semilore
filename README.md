# Inventory Tracking System — MVP Django Scaffold

This scaffold implements an MVP of the Inventory & Tracking system described in the uploaded system design. See original spec: `Inventory tracking system` file. File citation: fileciteturn0file0

What you get:
- Django project with `core` app (models, signals, tasks) and `api` app (DRF viewsets/serializers).
- Celery scaffold for background tasks.
- QR code generation using `qrcode` and saved to `MEDIA_ROOT/qrcodes`.
- CSV bulk import endpoint.
- Dockerfile and docker-compose for local testing with Postgres + Redis.

## Quickstart (local development, sqlite)
1. Create virtualenv (python3.11 recommended):
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Apply migrations:
   ```
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. Run development server:
   ```
   python manage.py runserver
   ```

4. Visit admin at http://localhost:8000/admin to create Faculties, Departments, Locations before creating Items.

## Using Docker (Postgres + Redis)
```
docker compose up --build
```
This will run migrations and start the dev server.

## Environment and production notes
- `DATABASE_URL` environment variable is supported for Postgres.
- `SECRET_KEY` and `DEBUG` should be set in environment for production.
- WeasyPrint requires native system libraries (pango, cairo, etc.). On Debian/Ubuntu install:
  `apt-get install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info` (already included in Dockerfile).

## Where files are:
- `core/models.py` — data models (Faculty, Department, Location, Item, Inspection, Transfer, AuditLog).
- `core/signals.py` — audit logging hooks.
- `core/tasks.py` — Celery tasks (overdue checker).
- `api/serializers.py` & `api/views.py` — DRF API (endpoints: /api/items/, /api/items/<pk>/inspect/, /api/items/bulk_import/ ...).
- `inventory_project/settings.py` — settings (supports DATABASE_URL or sqlite fallback).
- `docker-compose.yml` — quick local stack.

## Next steps & production hardening
- Integrate S3 for media (django-storages).
- Add authentication (SSO / LDAP) and granular RBAC as in spec.
- Add pagination, filtering, and search.
- Add unit tests and CI pipeline.
- Replace simple UID generation with DB sequence if multi-instance high concurrency required.

If you'd like, I can:
- Add LDAP/SSO example.
- Replace local media with S3 integration.
- Add front-end PWA scanner example.
"# main.barcode" 
