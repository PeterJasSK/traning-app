# Feature Plan — S1: Remove AWS, pick new photo storage + DB

**Epic:** [epic-vercel-mobile-rewrite.md](./epic-vercel-mobile-rewrite.md) — step 1 of 4
**Ticket:** none (developer-request epic; this repo has no linked GitHub issues)
**Slug:** remove-aws-storage-db
**Author:** Claude (Opus 4.8)
**Date:** 2026-07-11
**Status:** Complete
**Epic status:** Approved (open questions resolved 2026-07-11)

> **No automated tests** (project directive). Verification is manual only — see §7.

---

## 1. Summary

Cut every AWS/S3 and `django-storages` dependency out of `trener_app` and replace the
two things S3 was doing:

1. **Progress-photo storage** → a small custom Django `Storage` backend that talks to
   the **Vercel Blob** REST API (epic §6 Q1 decision: Vercel Blob, Hobby free tier).
2. **Database config** → read a single `DATABASE_URL` env var via `dj-database-url`,
   pointing at **Vercel Postgres** in production (epic §6 Q2), and falling back to the
   existing local `db.sqlite3` when `DATABASE_URL` is unset so local dev needs no
   Postgres install (epic §3).

This is the first epic step and depends on nothing. It must leave the app runnable
locally afterwards. Deployment wiring (WhiteNoise, `vercel.json`, WSGI adapter,
env-driven `ALLOWED_HOSTS`/`DEBUG`) is **S2** and explicitly out of scope here. Visual
redesign is **S3**. Full dead-code dedup and stray-file cleanup is **S4**.

---

## 2. Acceptance criteria

Copied from epic §7 S1 (verbatim), with IDs:

- **AC-1** ✅ — No references to `boto3`, `S3Boto3Storage`, or `AWS_*` settings remain
  anywhere in the codebase. **Covered by:** `grep -rniE 'boto3|s3boto3|aws_|django-storages'
  core/ trener_app/ requirements.txt` returns empty; AWS block removed from
  `trener_app/settings.py`, S3 imports removed from `core/models.py` / `core/views.py`.
- **AC-2** ✅ (backend wired; live round-trip needs token) — Model photo now uses the
  default storage `VercelBlobStorage` (`core/storage.py:40`), whose `url()`
  (`core/storage.py:92`) serves `measurement_detail.html` / `compare_photos.html` (both
  unchanged, use `{{ ...photo.url }}`). Field: `core/models.py:54`; default storage:
  `trener_app/settings.py:123`. Full upload→view→compare round-trip verified manually by
  the developer with `BLOB_READ_WRITE_TOKEN` set (§7 steps 5–9).
- **AC-3** ✅ — App runs locally against SQLite with no `DATABASE_URL` and against Postgres
  with it set, same settings file. **Covered by:** `trener_app/settings.py:82`
  (`dj_database_url.config` with SQLite default); verified — unset → `sqlite3` engine +
  `migrate` OK; `DATABASE_URL=postgres://…` → `postgresql` engine parsed.

Derived sub-criteria required to satisfy the above without breaking the app:

- **AC-1a** ✅ — `requirements.txt` no longer lists `boto3`, `botocore`, `s3transfer`,
  `django-storages`, or `jmespath`. **Covered by:** `requirements.txt` (10 lines; only
  `dj-database-url==3.1.2` @3 and `psycopg[binary]==3.3.4` @5 added).
- **AC-1b** ✅ — `"storages"` removed from `INSTALLED_APPS`. **Covered by:**
  `trener_app/settings.py:36` (app list no longer contains `"storages"`).
- **AC-2a** ✅ — Removing the S3 signed-URL preview view does not break the measurement
  list page: thumbnails resolve to the blob URL. **Covered by:**
  `core/templates/core/measurement_list.html:53-54` (`{{ measurement.photo.url }}`);
  `measurement_preview_url` view + route deleted (`core/views.py`, `core/urls.py`).

---

## 3. Scope

### In scope
- `requirements.txt` dependency swap.
- `trener_app/settings.py`: remove the entire AWS block + conditional S3 storage branch;
  add `dj-database-url`-based `DATABASE_URL` parsing with SQLite fallback; set the
  Django 5.2 `STORAGES` setting; provide a minimal local static-files config so the app
  still boots (WhiteNoise is S2).
- New `core/storage.py`: a `VercelBlobStorage` Django `Storage` subclass.
- `core/models.py`: drop the hardcoded `storage=S3Boto3Storage()` from `Measurement.photo`
  and the `storages` import; the field uses the default storage (`STORAGES["default"]`).
- `core/views.py`: remove the `boto3`/`S3Boto3Storage` imports, delete the
  `measurement_preview_url` view, and remove the S3 `?preview` block that sits inside the
  dead first `measurement_list` copy (only the S3 reference — see §5.5).
- `core/urls.py`: remove the `measurement_preview_url` route.
- `core/templates/core/measurement_list.html`: point the thumbnail `<img>`/`<a>` at
  `measurement.photo.url` instead of the deleted preview route (functional change only —
  no restyling; that is S3).
- One Doctrine-equivalent Django migration for the `Measurement.photo` `storage` change.

### Out of scope (deferred)
- Deployment config: `vercel.json`, WSGI adapter, WhiteNoise middleware, env-driven
  `ALLOWED_HOSTS`/`DEBUG`/`SECRET_KEY` — **S2** (epic §7 S2). `ALLOWED_HOSTS` keeps its
  current hardcoded values in this step.
- Mobile/responsive redesign and any cosmetic template edits — **S3**.
- Deleting the duplicate dead-code view definitions wholesale, un-tracking `db.sqlite3`,
  and removing stray PythonAnywhere files (`setup_push.sh`, `Terminal Saved Output.txt`)
  — **S4** (epic §7 S4). S1 touches the dead `measurement_list` copy **only** to strip
  its S3 reference, nothing more.
- Data migration from the old SQLite DB / S3 bucket / local `media/` — none (epic §6 Q5,
  fresh start).

---

## 4. Data model & migrations

No entity fields change. The only model diff is on `Measurement.photo`:

- **Before:** `models.ImageField(upload_to=user_directory_path, storage=S3Boto3Storage(), null=True, blank=True)`
- **After:** `models.ImageField(upload_to=user_directory_path, null=True, blank=True)` —
  storage resolves to `STORAGES["default"]` = `VercelBlobStorage`.

`upload_to=user_directory_path` is **kept unchanged** (epic §7 S1 conventions): it stays
the natural per-trainee key structure (`measurements/<username>/<date>_<filename>`).

Dropping the `storage=` kwarg produces one `AlterField` migration. Because no data
migration is planned and both the new Postgres DB and the Blob store start empty (epic §6
Q5), this migration is schema-cosmetic and safe to apply to a fresh DB.

- Run `python manage.py makemigrations core` and commit the generated migration.
- All DB access stays through the Django ORM — **no raw SQL** anywhere in this step.

---

## 5. Architecture & decisions

### 5.1 Database config (`settings.py`)
Replace the hardcoded SQLite `DATABASES` dict with:

```python
import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```

- `DATABASE_URL` unset → SQLite fallback (AC-3, local dev).
- `DATABASE_URL=postgres://…` → Postgres via `psycopg` (AC-3, Vercel Postgres).
- `psycopg[binary]` (psycopg 3) is the driver; it is the current recommended driver for
  Django 5.2 + Postgres.

### 5.2 `STORAGES` setting (Django 5.2)
Django 5.1+ **removed** `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE`; the current
`settings.py` still uses them inside the AWS branch. Replace the whole
`if AWS_STORAGE_BUCKET_NAME: … else: …` block with:

```python
STORAGES = {
    "default": {"BACKEND": "core.storage.VercelBlobStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
```

- `default` drives `Measurement.photo` (now that the field-level `storage=` is gone).
- `staticfiles` stays the plain Django backend in S1; **S2** swaps it to WhiteNoise's
  `CompressedManifestStaticFilesStorage`. Leaving it plain keeps S1 runnable and keeps
  the WhiteNoise decision inside S2 per the epic.
- No `MEDIA_ROOT`/`MEDIA_URL` needed — media lives in Vercel Blob, and the storage
  backend returns absolute blob URLs from `.url()`.

### 5.3 `VercelBlobStorage` backend (`core/storage.py`)
A thin, dependency-free `Storage` subclass (uses stdlib `urllib.request` — no new HTTP
dependency, keeping the epic's "as simple as possible" bar). Decorated with
`@deconstructible` so it is migration-serializable even if referenced by a field later.

Vercel Blob REST contract used:
- **Upload:** `PUT https://blob.vercel-storage.com/{pathname}` with headers
  `authorization: Bearer {BLOB_READ_WRITE_TOKEN}`, `x-api-version: 7`,
  `x-content-type: {mime}`, body = raw file bytes. Response JSON includes `url` and
  `pathname`.
- **Public read:** the returned `url` is a permanent public URL on the store's public
  host `https://{storeId}.public.blob.vercel-storage.com/{pathname}`.

Design points:
- **Random suffix left ON (Blob default).** `_save()` returns the **`pathname` from the
  API response** (which carries Blob's random suffix, e.g.
  `measurements/jan/2025-10-25_photo-3f9ab2.png`) and Django stores that as
  `photo.name`. `url()` then reconstructs `f"{base_url}/{name}"` with no extra API call.
  Keeping the random suffix makes blob URLs **unguessable**, which is what lets us delete
  the old S3 1-minute signed-URL preview view (§5.5) without a privacy regression — the
  URL itself is the access token, matching the previous "not directly guessable" behavior.
- **Lazy token read.** The token is read from settings inside `_save`/`delete`, **not**
  in `__init__`. `core/models.py` instantiates the default storage at import time; a
  lazy read means the app boots fine locally without `BLOB_READ_WRITE_TOKEN` set (you
  only need it to actually upload a photo).
- **Base URL derivation.** Default: derive the public host from the token
  (`vercel_blob_rw_{STOREID}_{SECRET}` → `https://{storeid}.public.blob.vercel-storage.com`,
  lowercased), overridable by an optional `VERCEL_BLOB_BASE_URL` env var. See §11 Q1.

Methods to implement (all type-hinted, `from __future__` not needed on 3.13):
- `_save(self, name: str, content: File) -> str` — PUT bytes, return response `pathname`.
- `url(self, name: str) -> str` — `f"{self._base_url()}/{name}"`.
- `exists(self, name: str) -> bool` — return `False` (skip Django's clobber-avoidance;
  `user_directory_path` + Blob's random suffix already make collisions effectively
  impossible).
- `delete(self, name: str) -> None` — best-effort `POST https://blob.vercel-storage.com/delete`
  with `{"urls": [self.url(name)]}`; there is no "delete measurement" flow today, so this
  is for completeness only.
- `_open(self, name: str, mode: str = "rb") -> File` — GET the public URL, wrap bytes in
  `django.core.files.base.ContentFile`. Low priority; templates only need `url()`, but
  include it so the `Storage` contract is complete.
- `size(self, name)` / `get_accessed_time` etc. — leave to `Storage` defaults / raise
  `NotImplementedError` where the base class does; not exercised by any current flow.

All type hints present, PSR-12-equivalent PEP 8 formatting, module-level docstring
explaining the Blob contract.

### 5.4 Model change (`core/models.py`)
- Remove `from storages.backends.s3boto3 import S3Boto3Storage` (line 4).
- Change the field to drop `storage=S3Boto3Storage()` (line 55). No other change.
- `user_directory_path` stays exactly as is.

### 5.5 View / URL / template changes
The old S3 access-control was a signed-URL indirection: `measurement_preview_url`
(`core/views.py:224`) generated a 1-minute `boto3` presigned URL, and
`measurement_list.html` linked its thumbnails through that route. With unguessable Vercel
Blob URLs (§5.3) the indirection is unnecessary, so:

- **`core/views.py`:**
  - Remove `from storages.backends.s3boto3 import S3Boto3Storage` (line 8) and
    `import boto3` (line 13).
  - Delete the `measurement_preview_url` view (lines 223–261).
  - Remove the S3 `?preview` block (lines ~180–196) that lives inside the **dead** first
    `measurement_list` copy — it references `S3Boto3Storage()` and would otherwise violate
    AC-1. **Only** that S3 block is touched; the rest of the dead duplicate is left for S4
    to delete wholesale (epic §7 S4). The live `measurement_list` is the second copy
    (line 522) and has no S3 code.
  - Remove `from django.conf import settings` (line 12) **iff** no other view still
    references `settings` after the deletions (verify with a grep during implementation;
    it is currently only used by the deleted AWS view).
- **`core/urls.py`:** remove the `measurement/<int:pk>/preview/` route (line 26).
- **`core/templates/core/measurement_list.html`:** change the thumbnail block (lines
  52–59) from `{% url 'measurement_preview_url' measurement.pk %}` (used in both the `<a
  href>` and `<img src>`) to `{{ measurement.photo.url }}`. This is the only template edit
  in S1 and is purely functional — no styling, no layout change (that is S3). The inline
  `style="width:50px"` is left untouched for S3 to handle.

`measurement_detail.html` and `compare_photos.html` already use
`{{ measurement.photo.url }}` / `{{ m.photo.url }}` and need **no** changes — the new
storage's `.url()` satisfies them (AC-2).

### 5.6 `requirements.txt`
- **Remove:** `boto3`, `botocore`, `s3transfer`, `django-storages`, `jmespath`
  (jmespath is a boto3-only transitive dep, safe to drop). `six` and `urllib3` are also
  boto3-transitive but harmless/possibly shared — leave them unless a post-change
  `pip freeze` shows them orphaned (note only, don't force).
- **Add:** `dj-database-url`, `psycopg[binary]`.
- **Keep:** `Django`, `pillow` (required by `ImageField`), `python-dateutil`,
  `python-dotenv`, `asgiref`, `sqlparse`.
- `whitenoise` and `gunicorn` are **S2** — do not add here.

---

## 6. File Plan

| # | File | Change | ACs |
|---|------|--------|-----|
| 1 | `requirements.txt` | Drop `boto3`/`botocore`/`s3transfer`/`django-storages`/`jmespath`; add `dj-database-url`, `psycopg[binary]` | AC-1a |
| 2 | `core/storage.py` **(new)** | `@deconstructible VercelBlobStorage(Storage)` — stdlib `urllib.request`; `_save` returns API `pathname`, `url()` = base+name, lazy token read, `exists`→False, best-effort `delete`, `_open` via public GET. Full type hints + docstring | AC-2 |
| 3 | `trener_app/settings.py` | Remove AWS block (lines 31–50) + `"storages"` from `INSTALLED_APPS`; replace `if AWS_STORAGE_BUCKET_NAME` static/media block with `STORAGES` + `STATIC_URL`/`STATIC_ROOT`; add `dj_database_url`-based `DATABASES`; update the module docstring (drop "AWS S3 + PythonAnywhere") | AC-1, AC-1b, AC-3 |
| 4 | `core/models.py` | Remove `storages` import (line 4); drop `storage=S3Boto3Storage()` from `Measurement.photo` (line 55) | AC-1, AC-2 |
| 5 | `core/views.py` | Remove `storages`+`boto3` imports (lines 8,13); delete `measurement_preview_url` (223–261); strip S3 `?preview` block from dead `measurement_list` copy (~180–196); remove `django.conf.settings` import if now unused | AC-1, AC-2a |
| 6 | `core/urls.py` | Remove `measurement_preview_url` route (line 26) | AC-2a |
| 7 | `core/templates/core/measurement_list.html` | Thumbnail `<a href>`/`<img src>` → `{{ measurement.photo.url }}` (lines 52–59); no restyle | AC-2, AC-2a |
| 8 | `core/migrations/000X_alter_measurement_photo.py` **(generated)** | `makemigrations core` for the `photo` storage-kwarg removal; commit as-is | AC-2 |

No file outside these is edited in S1.

---

## 7. Manual verification

All manual — no automated tests (project directive).

**Boot & config (AC-1, AC-3):**
1. `pip install -r requirements.txt` in a clean venv succeeds with no AWS packages pulled.
2. `grep -rniE 'boto3|s3boto3|aws_' core/ trener_app/ requirements.txt` returns nothing
   (AC-1 — remember the dead-copy S3 block must be gone too).
3. With **no** `DATABASE_URL`: `python manage.py migrate` then `python manage.py runserver`
   boots against `db.sqlite3`; log in and load `/measurements/` (AC-3 SQLite path).
4. With `DATABASE_URL=postgres://…` (a local or Vercel Postgres): `python manage.py migrate`
   creates the schema and `runserver` boots against Postgres (AC-3 Postgres path). If no
   Postgres is handy locally, at minimum confirm `dj_database_url.config()` parses the URL
   into the expected engine via `python manage.py shell`.

**Photo round-trip (AC-2)** — requires `BLOB_READ_WRITE_TOKEN` from the Vercel dashboard
in `.env`:
5. Log in as a **trainee**, `/measurements/add/`, submit a measurement **with a photo**;
   confirm the save succeeds and redirects to the list.
6. On `/measurements/` the thumbnail loads from a `*.public.blob.vercel-storage.com` URL
   (check the rendered `src`), and clicking it opens the full image (AC-2a).
7. Open that measurement's `measurement_detail.html` — the full image renders (AC-2).
8. As the owning **trainer**, open `compare_photos` for that trainee — both photo slots
   render from blob URLs (AC-2).
9. In the Vercel Blob dashboard, confirm the object appears under
   `measurements/<username>/<date>_<filename>` (path scheme preserved).

**Regression sanity:** log in as trainer and trainee; confirm charts, goals, and chat
pages still render (they don't touch storage, but they share `views.py`, which we edited).

---

## 8. Config / env vars introduced

| Var | Purpose | Required when |
|-----|---------|---------------|
| `DATABASE_URL` | Postgres connection string (Vercel Postgres in prod) | Prod; unset locally → SQLite |
| `BLOB_READ_WRITE_TOKEN` | Vercel Blob read/write token | Anytime a photo is uploaded/served |
| `VERCEL_BLOB_BASE_URL` *(optional)* | Override the public blob host if token-derivation is wrong | Fallback only — see §11 Q1 |

`.env` handling is unchanged (`python-dotenv` still loads `BASE_DIR/.env`). `.env` is
already git-ignored. These vars become Vercel Environment Variables in S2.

---

## 11. Open questions — resolved 2026-07-11

- **Q1 — Blob public base URL. RESOLVED: derive from token.** `VercelBlobStorage`
  derives `https://{storeId}.public.blob.vercel-storage.com` from
  `BLOB_READ_WRITE_TOKEN` (`vercel_blob_rw_{STOREID}_{SECRET}`), honoring an optional
  `VERCEL_BLOB_BASE_URL` override.

- **Q2 — HTTP client. RESOLVED: stdlib `urllib.request`.** No new HTTP dependency —
  keeps the epic's "as simple as possible" bar.

- **Q3 — psycopg flavor. RESOLVED: `psycopg[binary]` (psycopg 3).** Current
  Django-recommended driver, cleaner wheels on Python 3.13.

- **Q4 — The 3 sample images under `media/measurements/`. RESOLVED: leave as-is.** No
  Blob upload in S1; they stay on disk. The developer will use them to manually exercise
  the photo flow (§7) after S1 lands. (S4 decides whether to un-track them.)

---

## 13. Post-Implementation

**What was built (2026-07-11):**
- Removed every AWS/S3/`django-storages` dependency and config path. `requirements.txt`
  dropped `boto3`/`botocore`/`s3transfer`/`django-storages`/`jmespath` and added
  `dj-database-url==3.1.2` + `psycopg[binary]==3.3.4` (`six`/`urllib3` kept per §5.6 —
  `six` is still a `python-dateutil` dep).
- New `core/storage.py` → `@deconstructible VercelBlobStorage(Storage)`, stdlib-only
  (`urllib.request`), lazy token read, `_save` returns API `pathname`, `url()`=base+name,
  `exists`→False, best-effort `delete`, `_open` via public GET.
- `settings.py`: docstring de-AWS'd; AWS block + `"storages"` app removed; `DATABASES`
  now `dj_database_url.config(default=sqlite…, conn_max_age=600, conn_health_checks=True)`;
  legacy `if AWS_STORAGE_BUCKET_NAME` static/media branch replaced with the Django 5.2
  `STORAGES` dict + unconditional `STATIC_URL`/`STATIC_ROOT`.
- `models.py`: dropped `storages` import + field-level `storage=S3Boto3Storage()`; photo
  now resolves to `STORAGES["default"]`. Migration `0003_alter_measurement_photo.py`.
- `views.py`: removed `storages`/`boto3`/`django.conf.settings` imports (settings was only
  used by the deleted AWS view), deleted `measurement_preview_url`, stripped the S3
  `?preview` block from the dead first `measurement_list` copy (rest of the dead duplicate
  left for S4).
- `urls.py`: removed the `measurement_preview_url` route.
- `measurement_list.html`: thumbnail `<a>`/`<img>` → `{{ measurement.photo.url }}`.

**Verified:** `manage.py check` clean; `migrate` on SQLite OK; `DATABASE_URL` parses to
`postgresql`; login page HTTP 200 (with `DEBUG=True`); AC-1 grep empty.

**Follow-ups for the developer:**
- **Photo round-trip (§7 steps 5–9) still to run by hand** — needs a real
  `BLOB_READ_WRITE_TOKEN` (and, if token-derivation of the public host is wrong,
  `VERCEL_BLOB_BASE_URL`). Confirm the derived `*.public.blob.vercel-storage.com` base URL
  matches the actual store; §11 Q1 override exists for that case.
- The Vercel Blob REST contract (`x-api-version: 7`, PUT/`/delete`) was implemented from
  the documented API; validate against the live store on first upload.
- Pre-existing messiness left untouched per scope: duplicate view defs and the duplicate
  `compare_photos` route (urls.py) → **S4**; `SECURE_SSL_REDIRECT` causes a 301 on plain
  HTTP locally when `DEBUG` is unset (pre-existing, S2 territory).
- Installed Django is 5.2.6 locally while `requirements.txt` pins 5.2.8 — harmless, not
  changed.

## Notes on epic alignment
- Adopts epic §3/§6 decisions verbatim: Vercel Blob (Q1), Vercel Postgres (Q2), SQLite
  local fallback, no data migration (Q5). No re-litigation.
- Respects epic ordering: WhiteNoise, `vercel.json`, WSGI adapter, and env-driven
  `ALLOWED_HOSTS`/`DEBUG` are all left to **S2**; wholesale dead-code dedup and stray-file
  removal to **S4**. S1 only removes the S3 code path and wires the two replacement
  backends.
