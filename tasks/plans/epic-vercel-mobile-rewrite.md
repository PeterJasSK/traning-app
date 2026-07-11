# Epic: Vercel-ready, mobile-friendly rewrite (drop AWS)

**Slug:** vercel-mobile-rewrite
**Source:** developer request (no GitHub tickets — this repo has no linked GitHub issues)
**Author:** Claude (Sonnet 5)
**Date:** 2026-07-11
**Status:** Approved — open questions resolved 2026-07-11, pending developer approval

## 1. Why this epic exists

`trener_app` is a Slovak-language Django app for remote personal training: trainers manage
trainees, trainees log body measurements + progress photos, trainers view charts and
compare photos, and both sides chat. It currently targets PythonAnywhere (unfinished —
`ALLOWED_HOSTS` still has a placeholder domain) and stores progress photos on AWS S3 via
`django-storages`/`boto3`.

The developer wants to simplify and modernize the project with **minimal changes**:
1. Keep the existing Django app/domain model as-is (it's correct).
2. Make the UI phone-friendly (most trainees will use this on a phone).
3. Remove AWS/S3 entirely.
4. Make the project trivially deployable to Vercel.

This is explicitly a "make it simple" epic, not a feature epic — no new functionality is
in scope, only infra/design changes needed to hit those four goals.

## 2. Current-state findings (from codebase survey)

These are blocking facts any step below must account for:

- **DB is SQLite**, file-based (`db.sqlite3` at repo root, sometimes committed to git).
  Vercel's Python runtime is serverless with an ephemeral, mostly read-only filesystem —
  SQLite writes will not persist across requests/deploys. **A hosted Postgres is required**
  for Vercel, not optional.
- **Photo storage is hardwired to S3** at the model level: `core/models.py` sets
  `photo = models.ImageField(..., storage=S3Boto3Storage())` directly on the field,
  ignoring whatever `settings.py`'s conditional local/S3 branch says. Removing AWS means
  changing this field's storage, not just env vars.
- **Local `MEDIA_ROOT` won't work on Vercel either** — same ephemeral filesystem problem.
  Whatever replaces S3 must be an external store reachable over HTTP (Vercel Blob is the
  natural fit since it's a first-party Vercel product and keeps things "as simple as
  possible"; Cloudinary's free tier is the alternative if the developer wants a
  general-purpose CDN with transforms).
- **No production server / static-file setup exists**: no `gunicorn`, no `whitenoise`, no
  `vercel.json`, no WSGI adapter for Vercel's Python runtime. This all has to be added new.
- **`core/views.py` has duplicated view functions** (`add_measurement`,
  `measurement_list`, `measurement_detail`, `measurement_charts`, `goal_list`,
  `goal_add`, `goal_toggle_complete`, `chat_view` are each defined twice — Python
  silently uses the second definition, the first copies are dead code). This isn't part
  of the four goals, but the rewrite touches these exact files, so leaving known dead
  code in place while rewriting around it is worse than deleting it. Flagged as
  in-scope cleanup, not a new feature.
- **No CSS framework** — a single custom stylesheet (`core/static/core/style.css`,
  190 lines) with a viewport meta tag already in `base.html` but no mobile-first media
  queries; fixed-width forms/tables/footer. This is the target of the "phone friendly"
  and "rework the design" asks.
- Templates reference `measurement.photo.url` directly and rely on the storage
  backend's `.url()` method — this pattern is storage-agnostic and survives an S3 →
  Vercel Blob swap without template changes.

## 3. Cross-cutting decisions

These apply across all four steps below; later work should not re-litigate them.

- **Database:** move from SQLite to Postgres, read from a single `DATABASE_URL` env var
  (via `dj-database-url` or `django-environ`), matching how every "deploy Django to
  Vercel" guide and Vercel's own Postgres integrations expect config. Local dev can keep
  SQLite as a fallback when `DATABASE_URL` is unset, to avoid forcing local Postgres setup
  — this keeps local dev "as simple as possible" too.
- **Photo storage:** replace `S3Boto3Storage()` with Vercel Blob (`@vercel/blob`-style
  REST API via a small Django storage backend, or an existing `django-vercel-storage`
  style package if one exists and is maintained — otherwise a thin custom `Storage`
  subclass, since the interface is small). This is an open question for the developer —
  see §6.
- **Static files:** use WhiteNoise (`whitenoise` middleware) to serve static assets
  directly from the Django app under Vercel's Python runtime — simplest, no separate CDN
  config needed, no S3 dependency reintroduced for static files.
- **Deployment shape:** standard "Django on Vercel" pattern — a `vercel.json` routing all
  requests to a `api/index.py`-style WSGI handler wrapping `trener_app.wsgi.application`,
  `requirements.txt` at repo root (already present), and `DEBUG=False` / secrets driven
  entirely by Vercel environment variables (no more hardcoded `ALLOWED_HOSTS` IP/
  placeholder — read from env, default to `.vercel.app` wildcard + custom domain if any).
- **git-tracked `db.sqlite3`:** stop tracking it (it's dev-only under the new model) and
  remove other PythonAnywhere-specific leftovers (`setup_push.sh` if it's PA-specific,
  the stray `Terminal Saved Output.txt`) once confirmed unused — see §6.
- **Design rework:** no new JS framework, no build step (keep zero-build "as simple as
  possible") — rework `style.css` mobile-first with real breakpoints, fix the fixed-width
  forms/tables/footer, and refresh the visual style (colors/typography/spacing) in the
  same pass since it's the same file and the same review.
- **Scope discipline:** no changes to the domain model, URLs, permission logic, or
  chat/measurement/goal business logic. This is infra + presentation only.

## 4. Shared changes across steps

| Area | Change | Introduced by | Consumed by |
|------|--------|----------------|-------------|
| `requirements.txt` | drop `boto3`, `botocore`, `s3transfer`, `django-storages`; add `dj-database-url`, `psycopg[binary]` (or `psycopg2-binary`), `whitenoise`, `gunicorn` (harmless if unused locally), Blob-storage client lib | S1 | S1, S2 |
| `trener_app/settings.py` | remove all AWS_* settings + conditional storage block; add `DATABASE_URL` parsing, `whitenoise` middleware/static config, env-driven `ALLOWED_HOSTS`/`DEBUG`/`SECRET_KEY` | S1, S2 | S2 |
| `core/models.py` | `Measurement.photo` storage backend swapped from `S3Boto3Storage()` to new Blob storage class | S1 | S3 (templates keep using `.url()` unchanged) |
| `core/views.py` | remove `measurement_preview_url` (boto3 presigned-URL view) and any S3-specific branch in `measurement_list`; delete duplicate dead-code view definitions | S1 | — |
| `core/static/core/style.css`, `core/templates/*.html` | mobile-first rework + visual redesign | S3 | — |
| new: `vercel.json`, `api/index.py` (or equivalent WSGI entrypoint) | Vercel routing/build config | S2 | — |

## 5. Implementation order — the 4 steps

The developer asked for exactly 4 steps. Ordered so each step leaves the app in a
working, deployable-so-far state; S1 must precede S2 (can't deploy to Vercel with S3/
SQLite still wired in), S3 (design) is independent and can run in parallel with S1/S2 if
two people are working, S4 is a final integration/cleanup pass and must come last.

1. **S1 — Remove AWS, pick new photo storage + DB**
2. **S2 — Make it deployable to Vercel**
3. **S3 — Mobile-friendly responsive redesign**
4. **S4 — Cleanup + verification pass** (dead code, stray files, git-tracked db.sqlite3,
   end-to-end check that photo upload/view/compare, chat, and charts still work under
   the new storage + DB + hosting)

## 6. Decisions (resolved 2026-07-11)

- **Q1 — Photo storage:** must be free or have a free tier. **Vercel Blob's free
  ("Hobby") tier gives 1 GB storage / 1 GB bandwidth per month** — fine for a personal
  training app's progress photos, and keeps everything on one vendor (Q2 already picks
  Vercel Postgres). Decision: **Vercel Blob**, on the Hobby/free plan.
- **Q2 — Postgres provider:** integrate directly with Vercel. Decision: **Vercel
  Postgres** (Vercel's native Storage → Postgres integration, currently Neon-backed
  under the hood) — provisioned from the same Vercel dashboard as the deployment itself,
  free "Hobby" tier is enough for this app's scale.
- **Q3 — Design approach:** keep it simple, hand-rolled CSS. Decision: **no CSS
  framework** — rework `core/static/core/style.css` directly with mobile-first media
  queries and a visual refresh, exactly as drafted in §3/§7 S3. No Pico.css or similar.
- **Q4 — `db.sqlite3` / media in git:** just stop tracking now. Decision: add
  `db.sqlite3`, `.env`, and `media/` to `.gitignore` and `git rm --cached` them; **no**
  git history rewrite.
- **Q5 — Data migration:** fresh start. Decision: **no data migration** — the new
  Postgres DB and Vercel Blob store start empty; existing `db.sqlite3` rows and any
  photos in the S3 bucket or local `media/measurements/` are not carried over. (If the
  developer wants the 3 sample images under `media/measurements/` kept as fixtures/demo
  data, that's a one-off manual upload after S1 lands, not a migration step.)

All open questions are resolved; nothing left blocking implementation. This section
replaces the original "Open questions" list — decisions above are binding for
`/plan-feature` invocations against S1–S4.

## 7. Per-step briefs

### S1 — Remove AWS, pick new photo storage + DB
- **What it delivers:** All `boto3`/`django-storages`/S3 code and config removed;
  `Measurement.photo` now uses Vercel Blob as its storage backend; DB config reads
  `DATABASE_URL` with a Postgres driver (pointed at Vercel Postgres), falling back to
  SQLite when unset for local dev.
- **Acceptance criteria:**
  - No references to `boto3`, `S3Boto3Storage`, or `AWS_*` settings remain anywhere in
    the codebase.
  - Uploading a measurement photo, viewing it on `measurement_detail.html`, and using
    `compare_photos.html` all work end-to-end against the new storage backend.
  - App runs locally against SQLite with no `DATABASE_URL` set, and against Postgres
    with `DATABASE_URL` set, using the same settings file.
- **Likely files:** `trener_app/settings.py`, `core/models.py`, `core/views.py`,
  `requirements.txt`.
- **Depends on:** none (do first).
- **Conventions to follow:** keep the model's `upload_to=user_directory_path` naming
  scheme unchanged — no data migration is planned (fresh start), but the path scheme is
  still the natural key structure for a per-trainee blob layout.
- **Out of scope:** deployment config itself (S2), design (S3).

### S2 — Make it deployable to Vercel
- **What it delivers:** `vercel.json` + WSGI entrypoint wiring Django into Vercel's
  Python runtime, WhiteNoise for static files, env-driven `SECRET_KEY`/`DEBUG`/
  `ALLOWED_HOSTS`, and a working `vercel deploy` (or GitHub-integration auto-deploy).
- **Acceptance criteria:**
  - `vercel dev` (or a deployed preview) serves the login page, static CSS loads
    correctly, and at least one full user flow (login → view measurements) works.
  - No hardcoded IPs/placeholder domains remain in `ALLOWED_HOSTS`.
  - PythonAnywhere-specific settings/comments are removed from `settings.py`.
- **Likely files:** new `vercel.json`, new WSGI adapter file, `trener_app/settings.py`,
  `trener_app/wsgi.py`.
- **Depends on:** S1 (Vercel can't run against SQLite or S3-hardcoded storage).
- **Out of scope:** photo/DB backend choice itself (decided in S1), visual design (S3).

### S3 — Mobile-friendly responsive redesign
- **What it delivers:** `core/static/core/style.css` reworked mobile-first (real
  breakpoints, fluid forms/tables/nav/footer instead of fixed widths), plus a general
  visual refresh (colors, typography, spacing) across all templates in
  `core/templates/`. No CSS framework — hand-rolled only, per developer decision.
- **Acceptance criteria:**
  - All existing pages (home, measurement list/detail/add, compare photos, charts,
    goals, chat, trainee/trainer add/edit/delete, login/register) are usable and legible
    on a narrow (≤400px) viewport without horizontal scrolling, with the same
    functionality as today.
  - No layout regressions on desktop widths.
- **Likely files:** `core/static/core/style.css`, all files under `core/templates/`.
- **Depends on:** none — can proceed in parallel with S1/S2.
- **Out of scope:** any HTML structural/business-logic changes beyond what's needed for
  responsive layout; no new pages or features.

### S4 — Cleanup + verification pass
- **What it delivers:** Final integration pass once S1–S3 land: delete the duplicate
  dead-code view functions in `core/views.py`, stop tracking `db.sqlite3` in git (add to
  `.gitignore`), remove stray PythonAnywhere-era files if confirmed unused
  (`setup_push.sh`, `Terminal Saved Output.txt`) after checking with the developer, and
  do an end-to-end smoke test of every user flow against the final Vercel deployment.
- **Acceptance criteria:**
  - `core/views.py` has exactly one definition of each view function.
  - `git status` no longer tracks `db.sqlite3`; `.gitignore` covers it and any local
    `.env`.
  - A full manual pass (login as trainer + trainee, add measurement w/ photo, view
    chart, compare photos, send chat message, add/complete goal) succeeds on the live
    Vercel deployment.
- **Likely files:** `core/views.py`, `.gitignore`, repo root stray files.
- **Depends on:** S1, S2, S3 all merged.
- **Out of scope:** any new functionality.
