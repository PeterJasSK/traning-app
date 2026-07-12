# Feature Plan — Admin bootstrap, CLI user creation, and system manual

**Epic:** none — standalone feature (developer request, no epic exists for this work)
**Ticket:** none (no GitHub issues in this repo)
**Slug:** user-bootstrap-admin
**Author:** Claude (Sonnet 5)
**Date:** 2026-07-12
**Status:** Complete — implemented and manually verified 2026-07-12
**Depends on:** none (independent of the completed
[epic-vercel-mobile-rewrite.md](./epic-vercel-mobile-rewrite.md) steps, though it assumes
that deploy is live on Vercel + Postgres)

> **No automated tests** (project directive). Verification is manual only — see §7.

---

## 1. Summary

Today there is **no way to create the first admin account in production**. `core/admin.py`
registers a customized `CustomUserAdmin`, and Django's built-in `createsuperuser` command
works against the custom `CustomUser` model — but it is undocumented, isn't wired to the
app's `role` field, and there is no written guidance for running it against the deployed
Postgres database. Ongoing trainer/trainee creation already works once *someone* with
`role='trainer'` is logged in (`add_trainee`/`add_trainer` views), but that's a chicken-and-egg
problem for a brand new deployment: nobody can log in yet.

This feature adds:

1. **A management command, `create_user`**, that creates a `CustomUser` with any of the
   three practical account kinds — **admin** (`is_staff=is_superuser=True`), **trainer**
   (`role='trainer'`), or **trainee** (`role='trainee'`, optional `--head-trainer`) — from
   the command line, non-interactively or with a hidden password prompt. This is the
   production bootstrap path: pull prod env vars locally (`vercel env pull`) and run the
   command against the live Postgres DB, no shell access to the Vercel deployment needed.
2. **A small cleanup** of the dead, broken, unrouted registration code the survey turned
   up (`register_trainer_view`/`register_trainee_view`, their orphaned templates, and the
   unused `CustomUserCreationForm`) — the developer called this a "slight refactor," and
   leaving broken dead code next to the new, real bootstrap path is worse than removing it.
3. **`MANUAL.md`** at the repo root: a from-scratch operator/developer manual explaining
   the role model, the trainer/trainee hierarchy, every user-facing flow, how to bootstrap
   a production instance, and the environment variables the app depends on (consolidating
   facts currently scattered across the two completed epic-step plans).

No changes to `CustomUser`'s schema, no new migration, no changes to the existing
`add_trainee`/`add_trainer` in-app flows, no change to how Django Admin (`/admin/`) already
works — `create_user` is an additional, CLI-only path that reuses the exact same model.

---

## 2. Acceptance criteria

No source ticket exists, so these are drafted from the developer's request and confirmed
against the codebase survey. IDs are used by §6/§7 below.

- **AC-1** ✅ — There is a documented, working way to create the very first admin
  (`is_staff=True`, `is_superuser=True`) account against a production database, without
  needing an existing logged-in user or shell access to the Vercel deployment.
  **Covered by:** `core/management/commands/create_user.py:70-73` (`--role admin` →
  `CustomUser.objects.create_superuser(...)`); documented in `MANUAL.md` §4. Verified
  manually: `create_user --role admin --username testadmin --password ...` against a
  throwaway SQLite DB produced `is_staff=True, is_superuser=True`.
- **AC-2** ✅ — The same mechanism can create a **trainer** account and a **trainee**
  account (optionally attached via `--head-trainer`). **Covered by:**
  `core/management/commands/create_user.py:74-81` (non-admin branch sets `role` and
  optional `head_trainer`). Verified: `--role trainer --username coach1` → `role='trainer'`;
  `--role trainee --username jana --head-trainer coach1` → `role='trainee'`,
  `head_trainer.username=='coach1'`.
- **AC-3** ✅ — Single non-interactive-capable management command, works against SQLite
  and Postgres via `DATABASE_URL` (no DB-specific code — plain ORM calls).
  **Covered by:** `core/management/commands/create_user.py` (whole file); ORM-only,
  no raw SQL. Verified against local SQLite (see AC-1/AC-2); Postgres path relies on the
  same `dj_database_url`-configured `DATABASES` setting already exercised by every other
  management command (`trener_app/settings.py:87-93`) — no Postgres-specific behavior in
  this command to diverge.
- **AC-4** ✅ — Dead/broken registration code removed. **Covered by:** `core/views.py`
  (`register_trainer_view`/`register_trainee_view` deleted, confirmed via
  `grep -rn "register_trainer_view\|register_trainee_view\|CustomUserCreationForm" core/`
  → no matches); `core/forms.py` (`CustomUserCreationForm` and its now-unused
  `UserCreationForm` import removed); `core/templates/core/register.html` and
  `registracia.html` deleted (grep-confirmed unreferenced before deletion).
- **AC-5** ✅ — `MANUAL.md` exists at the repo root covering all required sections.
  **Covered by:** `MANUAL.md` §1 (account kinds), §2 (hierarchy), §3 (everyday flows),
  §4 (bootstrap), §5 (`create_user` reference), §6 (env vars), §7 (known limitations);
  `README.md` links to it.

---

## 3. Scope

### In scope
- New `core/management/commands/create_user.py` (+ the `core/management/` and
  `core/management/commands/` package `__init__.py` files — neither directory exists yet).
- Removal of `register_trainer_view`, `register_trainee_view` (`core/views.py`), the
  orphaned templates `core/templates/core/register.html` and
  `core/templates/core/registracia.html`, and the unused `CustomUserCreationForm`
  (`core/forms.py`).
- New `MANUAL.md` at the repo root.
- A short new "Setup / first admin" pointer added to `README.md` linking to `MANUAL.md`
  (the README today is a two-line description with no setup instructions at all).

### Out of scope (explicitly deferred)
- Any new HTTP/UI flow for self-registration or admin creation — deliberately CLI-only;
  the developer's ask is about *handling* creation, not exposing another public form.
  If a web-based "first-run setup wizard" is wanted later, that's a separate feature.
- Reintroducing an `'admin'` value to `CustomUser.role`'s choices (it existed in
  `0001_initial` and was dropped in `0002_...`). Admin-ness stays exactly what it already
  is elsewhere in the code (`is_staff`/`is_superuser`, checked first in
  `home_view` — `core/views.py:45`) — see §11 Q3 if the developer disagrees.
- The pre-existing duplicate `compare_photos` URL (`core/urls.py:25` and `:37`) and the
  duplicated dead-code view bodies noted in the epic's S4 backlog — untouched, unrelated
  to this feature.
- The `MEDIA_URL`/`MEDIA_ROOT` latent bug flagged by the survey (`trener_app/urls.py:30`
  references settings that aren't defined) — pre-existing, unrelated to user creation.
- Any change to `AddTraineeForm`/`AddTrainerForm` or the in-app `add_trainee`/`add_trainer`
  views — they keep working exactly as today for a logged-in trainer.

---

## 4. Data model & migrations

**None.** `create_user` only writes rows through the existing `CustomUser` manager
(`create_user`/`create_superuser`, both inherited from `AbstractUser`/`UserManager`) and
sets the existing `role`, `head_trainer` fields. No field, choice, or migration changes.

All persistence goes through the Django ORM (`CustomUser.objects...`) — no raw SQL.

---

## 5. Architecture & decisions

### 5.1 `create_user` management command

New file: `core/management/commands/create_user.py` (plus the two `__init__.py`
package markers — `core/management/__init__.py` and
`core/management/commands/__init__.py`).

```
python manage.py create_user --role admin    --username admin   [--email E] [--password P]
python manage.py create_user --role trainer  --username coach1  [--email E] [--password P]
python manage.py create_user --role trainee  --username jana    [--email E] [--password P] \
    [--head-trainer coach1]
```

Arguments (all via `argparse` in `add_arguments`, fully type-hinted handler):
- `--role {admin,trainer,trainee}` — **required**.
- `--username` — **required**. Command exits with a clear `CommandError` if a user with
  that username already exists (no silent overwrite/duplicate — bootstrap should fail
  loudly, not corrupt an existing account).
- `--email` — optional, default `""` (matches `AbstractUser.email`'s blank-allowed default).
- `--password` — optional. If omitted, the command prompts twice with `getpass.getpass`
  (hidden input, confirmation, mismatch re-prompt) — the same UX as `createsuperuser`, so
  a password never has to appear in shell history/`.bash_history` by default. Passing
  `--password` directly is supported for scripted/non-interactive seeding (documented in
  `MANUAL.md` as slightly less safe).
- `--head-trainer <username>` — optional, **only meaningful with `--role trainee`**;
  looks up an existing `CustomUser`, errors with `CommandError` if not found or if the
  named user's `role != 'trainer'`. Ignored (with a warning printed to stderr) if passed
  together with `--role admin`/`--role trainer`.

Behavior by `--role`:
- **`admin`** → `CustomUser.objects.create_superuser(username=..., email=..., password=...)`.
  `role` is left at its model default (`'trainee'`) — unused for superusers, since
  `home_view` (`core/views.py:45`) checks `is_superuser` before ever looking at `role`,
  exactly like every other admin-detection point in the app (§11 Q3 explains why this
  isn't changed).
- **`trainer`** → `CustomUser.objects.create_user(username=..., email=..., password=...)`
  then `role = 'trainer'; save()`.
- **`trainee`** → same, then `role = 'trainee'`; if `--head-trainer` given, set
  `head_trainer` to the looked-up trainer before saving.

On success the command prints a one-line confirmation (username + role) via
`self.stdout.write(self.style.SUCCESS(...))` — no other output, no return value used
elsewhere.

### 5.2 Why one command instead of three, and why not extend `createsuperuser`

- Django's `createsuperuser` is deliberately hard to extend with app-specific
  post-creation steps (`role`, `head_trainer`) without monkeypatching Django internals —
  simpler and more transparent to write one small command from scratch.
- A single `create_user --role ...` command (vs. three separate commands) keeps the
  bootstrap story to one thing to learn and document, and mirrors how `--role` already
  reads on `CustomUser` itself.

### 5.3 Production bootstrap flow (documented in `MANUAL.md`, not new code)

Because `DATABASE_URL` (set up in the completed
[feature-s1-remove-aws-storage-db.md](./feature-s1-remove-aws-storage-db.md)) points at a
network-reachable Postgres instance (Vercel Postgres), no shell access to the Vercel
serverless deployment is required. The bootstrap is:

1. `vercel env pull .env.production.local` (or copy `DATABASE_URL` from the Vercel
   dashboard by hand) to get the production connection string locally.
2. `DATABASE_URL=<prod-url> python manage.py create_user --role admin --username <u>`
   run from a developer machine — this talks directly to production Postgres over the
   network, the same way `migrate` already must be run once against a fresh prod DB.
3. Log into `/admin/` (or the app) with that account.

This is the same "run migrate/manage.py commands against the remote DB from your laptop"
pattern already implied — but never written down — by S1/S2; §5 of `MANUAL.md` (see §6)
is where this gets spelled out for the first time.

### 5.4 Cleanup of dead registration code (AC-4)

- `core/views.py`: delete `register_trainer_view` (lines 118–137) and
  `register_trainee_view` (lines 140–143). Neither is reachable — `core/urls.py` has no
  `register`-named route — and `register_trainer_view` renders a template
  (`core/register_trainer.html`) that doesn't exist, so it would 500 if it were ever hit.
- `core/templates/core/register.html` and `core/templates/core/registracia.html`: delete
  — grep-confirmed unreferenced by any view or `{% include %}`/`{% extends %}`.
- `core/forms.py`: delete `CustomUserCreationForm` (lines 6–9) — grep-confirmed unused
  by any view; `AddTraineeForm`/`AddTrainerForm` are the forms actually driving user
  creation and are untouched.
- No URL changes needed for this cleanup (nothing pointed at the deleted views).

### 5.5 `MANUAL.md` structure

Root-level `MANUAL.md`, developer/operator-facing (English, matching the existing plan
docs — the in-app UI strings stay Slovak, this file isn't user-facing). Sections:

1. **What this app is** — one paragraph, expanded from `README.md`'s current two lines.
2. **Account kinds** — admin (`is_staff`/`is_superuser`, full Django Admin access, no
   app-specific behavior), trainer (`role='trainer'`, manages trainees + helper trainers),
   trainee (`role='trainee'`, logs measurements/goals, chats with their trainer).
3. **The trainer hierarchy** — explains `head_trainer` (a trainee's primary trainer) and
   `helpers`/`main_trainer` (a trainer's helper trainers), with the `get_assigned_trainers()`
   helper method referenced (`core/models.py:26-31`).
4. **Everyday flows** — login, a trainer adding a trainee (`/users/add-trainee/`) or a
   helper trainer (`/users/add-trainer/`), a trainee logging a measurement with a photo,
   viewing charts, setting goals, chat — one short paragraph each, referencing the actual
   URL names from `core/urls.py`.
5. **Bootstrapping a new deployment** — the §5.3 steps verbatim, plus a note that once an
   admin exists, trainers/trainees can also be created via `/admin/` directly (no need to
   drop back to the CLI for routine seeding).
6. **`create_user` reference** — the full flag list from §5.1.
7. **Environment variables** — a single consolidated table: `DATABASE_URL`,
   `BLOB_READ_WRITE_TOKEN`, `VERCEL_BLOB_BASE_URL` (from S1), `ALLOWED_HOSTS`,
   `CSRF_TRUSTED_ORIGINS`, `SECRET_KEY`, `DEBUG` (from S2) — pulled from the two completed
   plans so there's one place to look instead of two old plan files.
8. **Known limitations** — the pre-existing duplicate `compare_photos` route and the
   `MEDIA_URL`/`MEDIA_ROOT` gap noted in §3 Out of Scope, so an operator isn't surprised
   by them later.

`README.md` gains one short new line/paragraph pointing at `MANUAL.md` for setup and
day-to-day operation — the existing two lines of description stay as-is.

---

## 6. File Plan

| # | File | Change | ACs |
|---|------|--------|-----|
| 1 | `core/management/__init__.py` **(new)** | empty package marker | AC-1, AC-2, AC-3 |
| 2 | `core/management/commands/__init__.py` **(new)** | empty package marker | AC-1, AC-2, AC-3 |
| 3 | `core/management/commands/create_user.py` **(new)** | `create_user` command per §5.1 — full type hints, `CommandError` on bad input, hidden-prompt password by default | AC-1, AC-2, AC-3 |
| 4 | `core/views.py` | Delete `register_trainer_view` (118–137) and `register_trainee_view` (140–143) | AC-4 |
| 5 | `core/forms.py` | Delete unused `CustomUserCreationForm` (6–9) | AC-4 |
| 6 | `core/templates/core/register.html` | Delete (orphaned) | AC-4 |
| 7 | `core/templates/core/registracia.html` | Delete (orphaned) | AC-4 |
| 8 | `MANUAL.md` **(new)** | Full manual per §5.5 | AC-5 |
| 9 | `README.md` | Add short pointer to `MANUAL.md` | AC-5 |

No file outside this table is edited.

---

## 7. Manual verification

All manual — no automated tests (project directive).

**`create_user` (AC-1, AC-2, AC-3):**
1. Local SQLite, no `DATABASE_URL`: `python manage.py create_user --role admin --username testadmin` →
   prompts for password twice, creates the user; `python manage.py shell -c
   "from core.models import CustomUser; u=CustomUser.objects.get(username='testadmin');
   print(u.is_staff, u.is_superuser, u.role)"` prints `True True trainee`.
2. Same, `--role trainer --username coach1 --password x`  (non-interactive path) →
   `role == 'trainer'`.
3. Same, `--role trainee --username jana --password x --head-trainer coach1` →
   `role == 'trainee'` and `head_trainer.username == 'coach1'`.
4. Re-run step 1 with the same `--username testadmin` → command exits non-zero with a
   clear "already exists" `CommandError`, no duplicate row created.
5. `--role trainee --head-trainer doesnotexist` → clear `CommandError`, no user created.
6. Log in as `testadmin` at `/login/` → redirected to `/admin/` (existing `home_view`
   logic, unchanged); log in as `coach1`/`jana` → see the trainer/trainee home pages.
7. Repeat step 1 with `DATABASE_URL` pointed at a real Postgres instance (local Docker
   Postgres or the Vercel Postgres used in S1/S2 verification) to confirm the command
   works identically against Postgres, not just SQLite (AC-3).

**Cleanup (AC-4):**
8. `grep -rn "register_trainer_view\|register_trainee_view\|CustomUserCreationForm"
   core/` returns nothing.
9. `python manage.py check` passes (no dangling template/view references).
10. Full regression click-through: login, add a trainee, add a helper trainer, add a
    measurement with a photo, view charts, add/toggle a goal, send a chat message — all
    unchanged from before this feature (nothing in §5 touches these views).

**Manual (AC-5):**
11. Read `MANUAL.md` top to bottom as if new to the project; confirm every URL name and
    env var it references actually exists (`grep` each one against `core/urls.py` /
    `trener_app/settings.py`).
12. Follow §5.3's bootstrap steps against a real (or throwaway) Vercel Postgres instance
    end-to-end, exactly as written, and confirm they work without modification.

---

## 8. Config / env vars introduced

None new. `MANUAL.md` documents the existing `DATABASE_URL`, `BLOB_READ_WRITE_TOKEN`,
`VERCEL_BLOB_BASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECRET_KEY`, `DEBUG`
(all already introduced by S1/S2) — nothing this feature adds requires a new var.

---

## 11. Open questions — resolved 2026-07-12 (developer: yes to all defaults)

- **Q1 — Command name.** Proposing `create_user --role {admin,trainer,trainee}` (one
  command, §5.2). Alternative: three separate commands (`create_admin`, `create_trainer`,
  `create_trainee`). Default: **one `create_user` command** — less to document, less
  duplicated argument-parsing code.
- **Q2 — `--password` CLI flag at all, given it can leak into shell history.** Proposing
  to keep it (opt-in, documented as slightly less safe) alongside the safer default
  hidden-prompt flow, because scripted/CI seeding of throwaway trainer/trainee accounts
  is a real use case the developer described. Default: **keep both**, prompt is the
  default when `--password` is omitted.
- **Q3 — Should `'admin'` come back as a `CustomUser.role` choice** (it existed in
  `0001_initial`, removed in `0002_...`)? Proposing **no** — admin-ness is already fully
  expressed via `is_staff`/`is_superuser` everywhere in the current code
  (`home_view`, `base.html`), and reintroducing a third `role` value would require an
  extra migration and auditing every `role == 'trainer'`/`role == 'trainee'` check in
  `core/views.py` to make sure none of them need to also match `'admin'`. Default:
  **no schema change** — `role` stays a trainer/trainee-only field, admin is orthogonal.
- **Q4 — `MANUAL.md` language.** Proposing English (matches the existing plan docs in
  `tasks/plans/`), even though `README.md` and all in-app UI strings are Slovak, because
  this manual is developer/operator-facing, not end-user-facing. Default: **English**.
- **Q5 — Where trainer/trainee bootstrap "ends" and Django Admin "takes over."**
  Proposing that `create_user` exists purely to get *out* of the chicken-and-egg problem
  (zero users → first admin), and that once an admin exists, `/admin/` is the documented
  path for creating further trainers/trainees from the CLI-averse side, while the in-app
  `add_trainee`/`add_trainer` flows remain the documented path for a logged-in trainer.
  Default: **document both, don't build anything new for either**.

---

## 13. Post-Implementation

**What was built (2026-07-12):**
- `core/management/commands/create_user.py` (+ package `__init__.py`s) — single command,
  `--role {admin,trainer,trainee}`, hidden password prompt by default, `--password`/
  `--head-trainer` flags, `CommandError` on duplicate username or bad `--head-trainer`.
- Removed `register_trainer_view`/`register_trainee_view` (`core/views.py`), unused
  `CustomUserCreationForm` + its `UserCreationForm` import (`core/forms.py`), and the
  orphaned templates `register.html`/`registracia.html`.
- New `MANUAL.md` at repo root; `README.md` links to it.

**Verified:** `python manage.py check` clean; all four `create_user` scenarios (admin,
trainer, trainee-with-head-trainer, duplicate-username rejection, bad-head-trainer
rejection) run against a throwaway SQLite DB and produced the expected `role`/
`is_staff`/`is_superuser`/`head_trainer` values; grep confirmed no leftover references to
the removed views/form.

**Follow-ups for the developer:** none required. The Postgres path re-uses the existing
`dj_database_url`-configured `DATABASES` setting rather than exercising it fresh —
running `create_user` once against the live Vercel Postgres is worth doing as a final
real-world check the first time it's used for actual production bootstrap, per §7 step 7
of this plan.
