"""Vercel serverless entrypoint — exposes the Django WSGI application."""

from trener_app.wsgi import application

app = application
