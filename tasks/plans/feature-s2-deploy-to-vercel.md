# Feature Plan — S2: Make it deployable to Vercel

**Epic:** [epic-vercel-mobile-rewrite.md](./epic-vercel-mobile-rewrite.md) — step 2 of 4
**Ticket:** none (developer-request epic; this repo has no linked GitHub issues)
**Slug:** deploy-to-vercel
**Author:** Claude (Opus 4.8)
**Date:** 2026-07-11
**Status:** Complete — implemented and manually verified locally 2026-07-11
**Epic status:** Approved (open questions resolved 2026-07-11)
**Depends on:** S1 ([feature-s1-remove-aws-storage-db.md](./feature-s1-remove-aws-storage-db.md)) — **Complete**

> **No automated tests** (project directive). Verification is manual only — see §7.

---

## 1. Summary

Wire the (now AWS-free) Django app into **Vercel's Python serverless runtime** so it
deploys with `vercel deploy` or the GitHub auto-deploy integration. Concretely S2 adds
the deployment shell around the app S1 left runnable-locally:

1. **WSGI entrypoint for Vercel** — a thin `api/index.py` that exposes
   `trener_app.wsgi.application` as the `app` callable Vercel's `@vercel/python` runtime
   invokes.
2. **`vercel.json`** — build + routing config sending every request to that entrypoint
   and running `collectstatic` at build time.
3. **WhiteNoise static serving** — add the WhiteNoise middleware and swap the S1
   placeholder `staticfiles` backend to WhiteNoise's compressed-manifest storage, so the
   app serves its own CSS under Vercel's Python runtime with no separate CDN (epic §3).
4. **Env-driven host/CSRF/proxy security config** — replace the hardcoded PythonAnywhere
   `ALLOWED_HOSTS` with an env-driven list defaulting to `.vercel.app`; add
   `CSRF_TRUSTED_ORIGINS` (POST login fails on the deployed domain without it) and
   `SECURE_PROXY_SSL_HEADER` (the S1-inherited `SECURE_SSL_REDIRECT` loops forever behind
   Vercel's TLS-terminating proxy without it).
5. **Remove PythonAnywhere leftovers from `settings.py`** — the hardcoded IP/placeholder
   host and the PA-specific comments (epic §7 S2 AC).

`SECRET_KEY` and `DEBUG` are already env-driven from S1 and need no change.
Photo/DB backend selection is **S1** (done). Visual redesign is **S3**. Deleting the
stray PA files at repo root (`setup_push.sh`, `Terminal Saved Output.txt`) and
un-tracking `db.sqlite3` are **S4** — S2 only touches `settings.py` code/comments.

---

## 2. Acceptance criteria

Copied from epic §7 S2 (verbatim), with IDs:

- **AC-1** — `vercel dev` (or a deployed preview) serves the login page, static CSS loads
  correctly, and at least one full user flow (login → view measurements) works. ✅
  Verified locally: `trener_app/settings.py` (WhiteNoise + WSGI wiring), `api/index.py`.
  Login page 200, CSS served with `Content-Type: text/css`, login POST → 302 → `/`,
  `/measurements/` → 200 (all under `DEBUG=True`, no `DATABASE_URL`, matching S1 state).
  Deployed-Vercel confirmation is a developer follow-up (§13).
- **AC-2** — No hardcoded IPs/placeholder domains remain in `ALLOWED_HOSTS`. ✅
  `trener_app/settings.py:28-30` — env-driven, default `.vercel.app,localhost,127.0.0.1`.
  `grep -i "13.40.136.139\|yourusername\|pythonanywhere" trener_app/settings.py` → no matches.
- **AC-3** — PythonAnywhere-specific settings/comments are removed from `settings.py`. ✅
  `trener_app/settings.py` — no `pythonanywhere`/PA-specific comment or IP string remains
  (grep confirmed clean); `SECURE_PROXY_SSL_HEADER`/CSRF/host comments rewritten for
  Vercel (`trener_app/settings.py:25-36`, `154-165`).

Derived sub-criteria required to satisfy the above without breaking the app:

- **AC-1a** — Vercel's Python runtime resolves a WSGI callable from `api/index.py` and
  every non-static route reaches Django (`vercel.json` routes + `api/index.py` exposing
  `app`). ✅ `api/index.py:1-4`, `vercel.json:1-16`.
- **AC-1b** — `{% static 'core/style.css' %}` (`base.html:8`) resolves to a URL that
  returns the stylesheet with `Content-Type: text/css` on the deployed site — i.e.
  `collectstatic` ran at build and WhiteNoise serves the result. ✅
  `trener_app/settings.py:53` (middleware), `:128-133` (storage backend). Verified
  locally: `collectstatic` produced `staticfiles/core/style.<hash>.css` +
  `staticfiles.json` manifest; `runserver` served it with `Content-Type: text/css` both
  under `DEBUG=True` and `DEBUG=False` (with `X-Forwarded-Proto: https`).
- **AC-1c** — The login form (a POST) succeeds on the deployed `*.vercel.app` origin — no
  CSRF 403 — which requires `CSRF_TRUSTED_ORIGINS` to include that origin. ✅
  `trener_app/settings.py:34-36`. Verified locally: login POST returned 302 (no CSRF
  403). Wildcard-origin behavior on the actual deployed domain is a developer follow-up
  (§13) — can't be curl-verified pre-deploy.
- **AC-1d** — With `DEBUG=False` the app does **not** enter an HTTPS redirect loop behind
  Vercel's proxy — requires `SECURE_PROXY_SSL_HEADER` so Django sees the forwarded scheme.
  ✅ `trener_app/settings.py:162-165`. Verified locally: `DEBUG=False` without the header
  → 301 redirect (would loop behind Vercel's proxy, which always delivers HTTP to the
  app); with `X-Forwarded-Proto: https` (simulating Vercel's edge) → 200, no redirect.
- **AC-1e** — App still boots and serves locally (`runserver`, `DEBUG=True`, no
  `DATABASE_URL`) exactly as after S1 — no regression from the WhiteNoise/host changes.
  ✅ Verified locally (see AC-1).

---

## 3. Scope

### In scope
- New `api/index.py` — Vercel WSGI entrypoint exposing `app`.
- New `vercel.json` — `@vercel/python` build for `api/index.py`, `collectstatic` build
  step, catch-all route to the entrypoint.
- New `build_files.sh` — build script that runs `collectstatic` (see §5.4; the default
  static strategy — §11 Q1 records the guaranteed fallback).
- `trener_app/settings.py`:
  - `ALLOWED_HOSTS` → env-driven, default `.vercel.app,localhost,127.0.0.1` (AC-2).
  - Remove PythonAnywhere comments on `ALLOWED_HOSTS` and the "…only on PythonAnywhere
    HTTPS" security comment (AC-3).
  - Add `whitenoise.middleware.WhiteNoiseMiddleware` immediately after
    `SecurityMiddleware`.
  - Swap `STORAGES["staticfiles"]` to
    `whitenoise.storage.CompressedManifestStaticFilesStorage`.
  - Add `CSRF_TRUSTED_ORIGINS` (env-driven, default `https://*.vercel.app`) (AC-1c).
  - Add `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` (AC-1d).
- `requirements.txt` — add `whitenoise` (and `gunicorn` per epic §4 — see §5.6).

### Out of scope (deferred)
- Photo storage / DB backend choice — **S1** (done); not touched.
- Mobile/responsive redesign, any CSS or template restyle — **S3**. S2 edits `base.html`
  only if the static-strategy fallback (§11 Q1) is chosen, and then only to confirm the
  `{% static %}` tag — no styling.
- Deleting duplicate dead-code view definitions, the duplicate `compare_photos` route,
  un-tracking `db.sqlite3`, and removing `setup_push.sh` / `Terminal Saved Output.txt` —
  **S4** (epic §7 S4).
- Removing the now-dead `if settings.DEBUG: static(MEDIA_URL, …)` block in
  `trener_app/urls.py` (media lives in Blob since S1). It is **harmless** today —
  `MEDIA_URL`/`MEDIA_ROOT` fall back to Django's global defaults (`""`), so `static()`
  returns `[]` and nothing breaks. Left for S4 to remove with the other cleanup.
- Data migration — none (epic §6 Q5, fresh start). Running `migrate`/`createsuperuser`
  against the empty Vercel Postgres is a **deploy step**, documented in §7/§8, not a code
  change.

---

## 4. Data model & migrations

**None.** S2 is deployment wiring only — no entities, fields, or migrations change. The
one operational note (not a code change): the target Vercel Postgres starts empty, so
after the first deploy the developer runs `python manage.py migrate` and
`createsuperuser` against it with `DATABASE_URL` pointed at Vercel Postgres (§7 step 1,
§8). All DB access remains through the Django ORM — **no raw SQL**.

---

## 5. Architecture & decisions

### 5.1 WSGI entrypoint (`api/index.py`)
Vercel's `@vercel/python` runtime imports the build's source module and invokes a
module-level WSGI/ASGI callable (it recognises `app`, `application`, or `handler`). We
reuse the existing, unchanged `trener_app/wsgi.py` (which already `setdefault`s
`DJANGO_SETTINGS_MODULE`) and expose it as `app`:

```python
"""Vercel serverless entrypoint — exposes the Django WSGI application."""

from trener_app.wsgi import application

app = application
```

- Full module docstring, no logic, PEP 8. `trener_app/wsgi.py` is **not** modified.
- Placing it under `api/` matches Vercel's convention (files in `api/` are serverless
  functions) and keeps the project root clean.

### 5.2 `vercel.json`
Route everything to the Python function; run `collectstatic` at build so WhiteNoise has
files to serve. Recommended baseline:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": { "runtime": "python3.12", "includeFiles": "staticfiles/**" }
    },
    {
      "src": "build_files.sh",
      "use": "@vercel/static-build",
      "config": { "distDir": "staticfiles" }
    }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "api/index.py" }
  ]
}
```

Decisions:
- **WhiteNoise serves `/static/*`, not a separate Vercel edge route** (epic §3: WhiteNoise
  is the chosen mechanism, "no separate CDN config"). Hence the single catch-all route —
  `/static/...` also flows into Django, where WhiteNoise's middleware short-circuits and
  returns the asset. `includeFiles: "staticfiles/**"` bundles the collected files into the
  function so WhiteNoise can read them at runtime.
- **`build_files.sh` runs `collectstatic`** via `@vercel/static-build` (Vercel already
  runs `pip install -r requirements.txt` for the Python build; the extra builder is only
  to trigger `collectstatic`). See §5.4.
- **Python runtime pinned to 3.12** — local dev is 3.13 but Vercel's Python runtime lags;
  3.12 is the safe, widely-supported target and Django 5.2 + `psycopg[binary]` run on it.
  See §11 Q2.
- Static-file serving on Vercel is the **#1 first-deploy risk** — §7 step 4 verifies it
  explicitly and §11 Q1 records the guaranteed fallback (commit `staticfiles/`, drop the
  static-build builder) if the build step or bundling misbehaves.

### 5.3 WhiteNoise wiring (`settings.py`)
- **Middleware:** insert `"whitenoise.middleware.WhiteNoiseMiddleware"` directly after
  `"django.middleware.security.SecurityMiddleware"` (WhiteNoise's documented position —
  it must run before everything except SecurityMiddleware).
- **Storage backend:** change `STORAGES["staticfiles"]["BACKEND"]` from the S1 placeholder
  `django.contrib.staticfiles.storage.StaticFilesStorage` to
  `whitenoise.storage.CompressedManifestStaticFilesStorage` (compresses + fingerprints
  assets; the manifest is produced by `collectstatic`). `STORAGES["default"]`
  (`core.storage.VercelBlobStorage`, from S1) is untouched.
- `STATIC_URL = "/static/"` and `STATIC_ROOT = BASE_DIR / "staticfiles"` (both already set
  by S1) are the collect target and the dir WhiteNoise serves — no change needed.
- No `MEDIA_ROOT`/`MEDIA_URL` (media is in Blob) — unchanged from S1.

### 5.4 `build_files.sh`
```bash
#!/bin/bash
# Vercel build step: collect static assets for WhiteNoise to serve.
python3 manage.py collectstatic --noinput --clear
```
- Executable (`chmod +x`). Requirements are already installed by Vercel's Python build
  before this runs; if the static-build builder runs in an isolated env, prepend
  `pip install -r requirements.txt`. Verify on first deploy (§7 step 4).
- `--noinput` for non-interactive build; `--clear` keeps the output deterministic.

### 5.5 Host / CSRF / proxy security (`settings.py`)
Replace the hardcoded PA `ALLOWED_HOSTS` block and add the two Vercel-proxy settings:

```python
# Hosts allowed to serve the app; on Vercel this is the *.vercel.app preview/prod
# domain (and any custom domain). Overridable via the ALLOWED_HOSTS env var
# (comma-separated).
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS", ".vercel.app,localhost,127.0.0.1"
).split(",")

# Django 4+ requires the deployed origin here for POST forms (e.g. login) to pass
# CSRF checks. Scheme is mandatory.
CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS", "https://*.vercel.app"
).split(",")
```

And near the existing `SECURE_SSL_REDIRECT` block (inherited from S1):

```python
# Vercel terminates TLS at its edge and forwards over HTTP with this header.
# Without it, SECURE_SSL_REDIRECT (below, when DEBUG is False) never sees "https"
# and redirect-loops forever.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

- The leading dot in `.vercel.app` is Django's subdomain-wildcard form and matches every
  preview/prod deployment host — no per-deploy edits (AC-2).
- Remove the comment `# PythonAnywhere requires your domain here` and the
  `# Security (enable fully only on PythonAnywhere HTTPS)` / `# Only redirect HTTPS ON
  PRODUCTION` PA-flavoured comments; replace with Vercel-accurate wording (AC-3).
- `SECRET_KEY`/`DEBUG` already read from env (S1) — unchanged. On Vercel, `DEBUG` is unset
  → `False`, which correctly activates `SECURE_SSL_REDIRECT` + HSTS (now safe thanks to
  `SECURE_PROXY_SSL_HEADER`).

### 5.6 `requirements.txt`
- **Add:** `whitenoise` (static serving under the Python runtime).
- **Add:** `gunicorn` — epic §4 lists it ("harmless if unused"). Vercel's serverless
  runtime invokes the WSGI `app` directly and does **not** use gunicorn; it is kept only
  for any non-Vercel/local WSGI serving. See §11 Q3 (default: keep, per epic — do not
  re-litigate).
- **Keep** everything S1 left: `Django`, `dj-database-url`, `psycopg[binary]`, `pillow`,
  `python-dateutil`, `python-dotenv`, `asgiref`, `sqlparse`, `six`, `urllib3`.
- Pin `whitenoise` to a current release (e.g. `whitenoise==6.11.0`) to match the pinned
  style of the file; confirm the exact latest at implementation time.

---

## 6. File Plan

| # | File | Change | ACs |
|---|------|--------|-----|
| 1 | `api/index.py` **(new)** | WSGI entrypoint: `from trener_app.wsgi import application` then `app = application`. Docstring, no logic. | AC-1, AC-1a |
| 2 | `vercel.json` **(new)** | `@vercel/python` build of `api/index.py` (runtime `python3.12`, `includeFiles: staticfiles/**`); `@vercel/static-build` of `build_files.sh` (distDir `staticfiles`); single catch-all route `/(.*) → api/index.py`. | AC-1, AC-1a, AC-1b |
| 3 | `build_files.sh` **(new)** | `#!/bin/bash` + `python3 manage.py collectstatic --noinput --clear`; executable. | AC-1b |
| 4 | `requirements.txt` | Add `whitenoise` (+ `gunicorn` per epic §4). | AC-1b |
| 5 | `trener_app/settings.py` | Env-driven `ALLOWED_HOSTS` (default `.vercel.app,localhost,127.0.0.1`); add `CSRF_TRUSTED_ORIGINS` + `SECURE_PROXY_SSL_HEADER`; insert WhiteNoise middleware after SecurityMiddleware; swap `STORAGES["staticfiles"]` → WhiteNoise `CompressedManifestStaticFilesStorage`; remove PA comments. | AC-1b, AC-1c, AC-1d, AC-2, AC-3 |

No other file is edited in S2. `trener_app/wsgi.py`, `core/`, templates, and the S1
`STORAGES["default"]`/`DATABASES` config are untouched. (If §11 Q1 fallback is chosen:
drop file #3 and the static-build builder from `vercel.json`, and add a committed
`staticfiles/` directory — noted there.)

---

## 7. Manual verification

All manual — no automated tests (project directive). Ordered local-first, then deploy.

**Local no-regression (AC-1e) — before deploying:**
1. Clean venv, `pip install -r requirements.txt` — `whitenoise` installs, no errors.
2. `python manage.py check` is clean; `python manage.py collectstatic --noinput` writes
   `staticfiles/` including a hashed `core/style.<hash>.css` + `staticfiles.json` manifest.
3. `python manage.py runserver` (DEBUG=True, no `DATABASE_URL`): login page loads, CSS
   applied, log in → `/measurements/` renders (same as post-S1).
4. Sanity-check `DEBUG=False` locally (e.g. `DEBUG=False python manage.py runserver
   --insecure`): confirm WhiteNoise serves `/static/core/style.<hash>.css` with
   `Content-Type: text/css` (AC-1b) and no redirect loop.

**Deploy (AC-1, AC-1a–d, AC-2, AC-3):**
5. In the Vercel dashboard set env vars (§8): `SECRET_KEY`, `DATABASE_URL` (Vercel
   Postgres), `BLOB_READ_WRITE_TOKEN` (Vercel Blob), and leave `DEBUG` unset (→ False).
6. First deploy (`vercel deploy` or push to the GitHub-integrated branch). Confirm the
   build log shows `collectstatic` running (AC-1b) and the function builds.
7. One-off: with `DATABASE_URL` pointed at Vercel Postgres locally, run
   `python manage.py migrate` then `createsuperuser` (the serverless runtime can't migrate
   itself; §8).
8. Open the deployed URL: **login page renders and its CSS loads** (view source → the
   `<link>` resolves to a 200 `text/css`) (AC-1, AC-1b).
9. **Log in** (the POST must not 403) and land on `/measurements/` — full flow works
   (AC-1, AC-1c). If it 403s, `CSRF_TRUSTED_ORIGINS` needs the exact deploy origin.
10. Confirm the page is served over HTTPS with **no redirect loop** (AC-1d). A loop means
    `SECURE_PROXY_SSL_HEADER` is missing/wrong.
11. View the deployed site's host in the URL — it's a `*.vercel.app` domain accepted by
    the wildcard `ALLOWED_HOSTS` with no hardcoded IP anywhere (AC-2); grep `settings.py`
    confirms no `pythonanywhere`/IP strings/PA comments remain (AC-3).

**If static assets 404 on the deployed site (the known risk):** apply the §11 Q1
fallback and redeploy.

---

## 8. Config / env vars introduced

Set as **Vercel Environment Variables** (Production + Preview). S1's vars still apply.

| Var | Purpose | Required |
|-----|---------|----------|
| `SECRET_KEY` | Django secret (S1; must be a real secret in prod, not the dev default) | Prod |
| `DATABASE_URL` | Vercel Postgres connection string (S1) | Prod |
| `BLOB_READ_WRITE_TOKEN` | Vercel Blob token (S1) | Prod (photo upload/serve) |
| `DEBUG` | Leave unset in prod → `False` (S1) | — |
| `ALLOWED_HOSTS` *(optional)* | Override the `.vercel.app,localhost,127.0.0.1` default (e.g. add a custom domain) | Custom domain only |
| `CSRF_TRUSTED_ORIGINS` *(optional)* | Override the `https://*.vercel.app` default (e.g. add a custom domain) | Custom domain only |

**One-off deploy commands** (not code): `python manage.py migrate` and `createsuperuser`
against Vercel Postgres after the first deploy (§7 step 7).

---

## 11. Open questions — resolved 2026-07-11 (developer: yes to all defaults, no custom domain)

- **Q1 — Static-file build strategy. RESOLVED: build-script default.** Ship the
  `build_files.sh` + `@vercel/static-build` builder running `collectstatic`, with
  `includeFiles: "staticfiles/**"` bundling the result into the Python function (WhiteNoise
  serves it). **Guaranteed fallback if it 404s on first deploy** (§7 step 8): run
  `collectstatic` locally and **commit `staticfiles/`** to git, removing `build_files.sh`
  and the static-build builder from `vercel.json`; `@vercel/python` then bundles the
  committed dir. Try the default first, fall back only if needed.

- **Q2 — Python runtime version. RESOLVED: pin `python3.12`** in `vercel.json` (Django 5.2
  + `psycopg[binary]` fully supported). Bump to 3.13 only if the Vercel account already
  offers it.

- **Q3 — `gunicorn` in `requirements.txt`. RESOLVED: keep it** per epic §4 (unused on
  Vercel serverless, harmless).

- **Q4 — Custom domain. RESOLVED: none for this step.** Ship the `.vercel.app` wildcard
  defaults for `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`; a custom domain later is just the
  two env vars (§8), no code change.

---

## 13. Post-Implementation

Built exactly per §6 File Plan: `api/index.py` (WSGI entrypoint), `vercel.json`
(`@vercel/python` + `@vercel/static-build` builders, catch-all route), `build_files.sh`
(`collectstatic`), `requirements.txt` (+`whitenoise==6.12.0`, +`gunicorn==26.0.0`), and
`trener_app/settings.py` (env-driven `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`, WhiteNoise
middleware + storage backend, `SECURE_PROXY_SSL_HEADER`, PA comments removed).

All AC-1/1a–1e, AC-2, AC-3 verified **locally** (venv `runserver`, both `DEBUG=True` and
`DEBUG=False` with a simulated `X-Forwarded-Proto: https` header) — see §2 for the exact
evidence. Not yet verified: an actual Vercel deploy (§7 steps 5–11), which the developer
must run — this requires Vercel account/dashboard access (env vars, Postgres, Blob
provisioning) not available in this session. Follow-ups for the developer:

1. Push to the GitHub-integrated branch or run `vercel deploy`.
2. Set `SECRET_KEY`, `DATABASE_URL` (Vercel Postgres), `BLOB_READ_WRITE_TOKEN` (Vercel
   Blob) as Vercel env vars; leave `DEBUG` unset.
3. Run `migrate` + `createsuperuser` against the new Postgres (§7 step 7, §8).
4. Confirm the deployed site per §7 steps 8–11 (login flow, static CSS, no redirect
   loop, `*.vercel.app` host). If static assets 404, apply the §11 Q1 fallback (commit
   `staticfiles/`, drop `build_files.sh` + the static-build builder).

No deviations from the plan. No scope beyond §3 "In scope" was touched.

## Notes on epic alignment
- Adopts epic §3/§7 S2 decisions verbatim: WhiteNoise for static (no separate CDN),
  standard "Django on Vercel" `vercel.json` + WSGI-adapter shape, env-driven
  `ALLOWED_HOSTS`/`DEBUG`/`SECRET_KEY`, `DEBUG=False`-driven secrets. No re-litigation of
  S1's Blob/Postgres choices.
- Respects epic ordering: no domain-model/URL/business-logic changes; dead-code dedup,
  stray-file removal, and un-tracking `db.sqlite3` stay in **S4**; visual redesign stays
  in **S3**. S2 adds only the deployment shell + the WhiteNoise/host/CSRF/proxy settings
  the deploy actually requires.
- Additions beyond the epic's literal list (`CSRF_TRUSTED_ORIGINS`,
  `SECURE_PROXY_SSL_HEADER`) are not new scope — they are the minimum required for the
  epic's own AC ("at least one full user flow (login → view measurements) works") to pass
  on Vercel, since login is a POST behind a TLS-terminating proxy.
