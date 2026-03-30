"""
Passenger WSGI Entry Point — GoDaddy cPanel Shared Hosting
===========================================================
GoDaddy cPanel → Hosting → Python App → Application startup file: passenger_wsgi.py

cPanel's Phusion Passenger automatically activates the virtualenv it created for
your Python app. This file simply sets the environment and hands control to Flask.

DO NOT rename this file — cPanel's Passenger looks for it by this exact name
unless you explicitly set a different startup file in the cPanel Python App panel.
"""
import sys
import os

# Ensure the project root is on the Python path so all imports resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force production mode
os.environ.setdefault("FLASK_ENV", "production")

from app import create_app  # noqa: E402

# `application` is the required Passenger-WSGI callable name — do not rename
application = create_app()
