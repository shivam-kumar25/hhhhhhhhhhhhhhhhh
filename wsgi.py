"""
WSGI Entry Point — DSTAIR
=========================
Universal entry point used by all production deployment methods:
  - Gunicorn  (VPS, Railway, Render, Heroku)
  - Passenger (GoDaddy cPanel shared hosting)
  - Waitress  (Windows IIS / direct run)

The WSGI spec requires a callable named `application`.
Gunicorn / Procfile uses `app` by convention — both are exposed here.
"""
import os

# Force production mode. Override by setting FLASK_ENV in your .env or server env vars.
os.environ.setdefault("FLASK_ENV", "production")

from app import create_app  # noqa: E402 — must come after env setup

application = create_app()   # WSGI standard (Passenger, uWSGI)
app = application            # Gunicorn / Procfile alias
