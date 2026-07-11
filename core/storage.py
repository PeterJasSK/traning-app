"""
Vercel Blob storage backend for Django.

A thin, dependency-free ``Storage`` subclass that stores files in Vercel Blob
via its REST API (https://vercel.com/docs/vercel-blob). It uses only the Python
standard library (``urllib.request``) so no extra HTTP dependency is required.

Blob REST contract used here:

* Upload:  ``PUT https://blob.vercel-storage.com/{pathname}`` with headers
  ``authorization: Bearer {BLOB_READ_WRITE_TOKEN}``, ``x-api-version: 7`` and
  ``x-content-type: {mime}``; the body is the raw file bytes. The JSON response
  contains ``url`` and ``pathname`` (the pathname carries Blob's random suffix,
  which keeps the public URL unguessable).
* Read:    the returned ``url`` is a permanent public URL on the store's public
  host ``https://{storeId}.public.blob.vercel-storage.com/{pathname}``.
* Delete:  ``POST https://blob.vercel-storage.com/delete`` with a JSON body of
  ``{"urls": [<url>]}``.

The read/write token is read lazily (inside the methods that need it, not in
``__init__``) so the app — and ``core.models``, which instantiates the default
storage at import time — boots locally without ``BLOB_READ_WRITE_TOKEN`` set.
You only need the token to actually upload or delete a blob.
"""

import json
import mimetypes
import os
import urllib.request

from django.core.files.base import ContentFile, File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

API_BASE_URL = "https://blob.vercel-storage.com"
API_VERSION = "7"


@deconstructible
class VercelBlobStorage(Storage):
    """Django storage backend backed by the Vercel Blob REST API."""

    def _token(self) -> str:
        """Read the read/write token lazily from the environment."""
        token = os.getenv("BLOB_READ_WRITE_TOKEN")
        if not token:
            raise ValueError(
                "BLOB_READ_WRITE_TOKEN is not set; it is required to "
                "upload or delete Vercel Blob objects."
            )
        return token

    def _base_url(self) -> str:
        """
        Public base URL for reading blobs.

        Defaults to the store-scoped public host derived from the token
        (``vercel_blob_rw_{STOREID}_{SECRET}`` ->
        ``https://{storeid}.public.blob.vercel-storage.com``), and can be
        overridden with the optional ``VERCEL_BLOB_BASE_URL`` env var.
        """
        override = os.getenv("VERCEL_BLOB_BASE_URL")
        if override:
            return override.rstrip("/")

        parts = self._token().split("_")
        # vercel_blob_rw_{STOREID}_{SECRET}
        store_id = parts[3] if len(parts) >= 4 else ""
        return f"https://{store_id.lower()}.public.blob.vercel-storage.com"

    def _save(self, name: str, content: File) -> str:
        """Upload the file bytes to Vercel Blob and return the stored pathname."""
        content_type = (
            mimetypes.guess_type(name)[0] or "application/octet-stream"
        )
        request = urllib.request.Request(
            f"{API_BASE_URL}/{name}",
            data=content.read(),
            method="PUT",
            headers={
                "authorization": f"Bearer {self._token()}",
                "x-api-version": API_VERSION,
                "x-content-type": content_type,
            },
        )
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
        # The API-assigned pathname carries Blob's random suffix; store it so
        # url() can reconstruct the public URL without another API call.
        return payload.get("pathname", name)

    def url(self, name: str) -> str:
        """Return the permanent public URL for a stored blob."""
        return f"{self._base_url()}/{name}"

    def exists(self, name: str) -> bool:
        """
        Always report the name as free.

        ``user_directory_path`` plus Blob's random suffix make collisions
        effectively impossible, so Django's clobber-avoidance rename loop is
        unnecessary.
        """
        return False

    def delete(self, name: str) -> None:
        """Best-effort delete of a blob (no measurement-delete flow uses this)."""
        request = urllib.request.Request(
            f"{API_BASE_URL}/delete",
            data=json.dumps({"urls": [self.url(name)]}).encode("utf-8"),
            method="POST",
            headers={
                "authorization": f"Bearer {self._token()}",
                "x-api-version": API_VERSION,
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(request):
            pass

    def _open(self, name: str, mode: str = "rb") -> File:
        """Fetch a blob's bytes over its public URL and wrap them in a File."""
        with urllib.request.urlopen(self.url(name)) as response:
            data = response.read()
        return ContentFile(data, name=name)
