# Lost & Found Community Platform

> **Client project:** This application was developed for a client. It is published here as a portfolio and technical reference project. Client-specific reports, local databases, uploaded files, and development environments are intentionally excluded from the repository.

A full-stack community lost-and-found web application built with Flask. It lets community members report lost or found items, search listings, submit ownership claims, and follow a role-based moderation workflow.

## Features

- Buyer, seller, and administrator roles
- Lost/found item reporting with image uploads and location details
- Searchable and filterable listings
- Privacy-aware ownership claims with private verification details
- Administrator approval and claim-review workflows
- Notifications, profiles, dashboards, and map support
- Seeded demonstration data
- Automated workflow tests

## Tech stack

- Python and Flask
- Flask-SQLAlchemy with SQLite by default
- Flask-Login and Flask-WTF
- Jinja templates, HTML, CSS, and JavaScript
- Pillow for image handling
- Pytest

## Local setup

Python 3.12 or newer is recommended.

```bash
python -m venv .venv
```

Activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies and start the app:

```bash
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>.

On Windows, `setup.bat` and `run.bat` provide the same setup and start flow.

## Configuration

Copy `.env.example` values into your shell or deployment platform's environment settings. At minimum, replace `SECRET_KEY` and `ADMIN_REGISTRATION_CODE` outside local development.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs sessions and CSRF tokens |
| `ADMIN_REGISTRATION_CODE` | Protects administrator registration |
| `DATABASE_URL` | Optional SQLAlchemy database URL; defaults to local SQLite |

The application creates its database and seed data automatically on first start. Runtime databases and user uploads are not committed.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Administrator | `admin@lostfound.local` | `Admin@123` |
| Seller | `seller@lostfound.local` | `Seller@123` |
| Buyer | `buyer@lostfound.local` | `Buyer@123` |

These credentials are for local demonstration only and must not be used in production.

## Tests

```bash
python -m pytest -q
```

The test suite covers seed consistency, authentication and authorization, role dashboards, registration, the complete report-to-claim workflow, and ownership protection.

## Deployment note

GitHub hosts the source code and runs the automated tests. Because this is a server-side Flask application, GitHub Pages cannot run it directly. Deploy it to a Python-capable service and configure secure environment variables and a persistent database before production use.

