# trener_app manual

Operator/developer manual for `trener_app` — a Slovak-language Django app for remote
personal training. A trainer manages trainees remotely: trainees log body measurements
and progress photos, trainers view charts and compare photos over time, and both sides
chat. The in-app UI text is Slovak; this manual is written for whoever runs and maintains
the deployment, so it's in English.

## 1. Account kinds

There are three practical kinds of account, but only one model field and two Django
built-in flags drive the distinction:

| Kind | How it's identified | Capabilities |
|------|----------------------|--------------|
| **Admin** | `is_staff=True`, `is_superuser=True` | Full Django Admin (`/admin/`) access — can create/edit/delete any user, measurement, goal, or message directly. No app-specific behavior beyond that. |
| **Trainer** | `role='trainer'` on `CustomUser` | Manages trainees and helper trainers, views their charts, compares photos, chats with assigned trainees. |
| **Trainee** | `role='trainee'` on `CustomUser` (the default) | Logs their own measurements/photos, sets goals, chats with their trainer(s). |

`role` is a plain `CharField` with only `trainer`/`trainee` as valid choices — there is no
`role='admin'` value. Admin-ness is entirely orthogonal to `role`: a superuser's `role`
field is left at its default (`'trainee'`) and is simply never consulted, because every
admin check in the app (e.g. `home_view`) tests `is_superuser` first, before ever looking
at `role`.

## 2. The trainer hierarchy

- **`head_trainer`** — a self-referential foreign key on `CustomUser`. For a trainee, this
  is their one primary trainer. Set automatically when a trainer adds a trainee.
- **`helpers`** / **`main_trainer`** — a self-referential many-to-many. A trainer can have
  helper trainers (`helpers`); from a helper trainer's side, the reverse relation
  (`main_trainer`) lists which trainer(s) they help.
- **`get_assigned_trainers()`** — a `CustomUser` method a trainee can call to get the
  combined list of their `head_trainer` plus any trainers who have them via `main_trainer`
  (i.e. every trainer allowed to see/chat with this trainee).

## 3. Everyday flows

- **Login** — `/login/`. Standard username/password form; on success, `home_view`
  redirects to `/admin/` for superusers, the trainer dashboard for `role='trainer'`, or
  the trainee dashboard for `role='trainee'`.
- **A trainer adds a trainee** — `/users/add-trainee/`. Sets `role='trainee'` and
  `head_trainer` to the logged-in trainer.
- **A trainer adds a helper trainer** — `/users/add-trainer/`. Sets `role='trainer'` and
  adds the logged-in trainer to the new trainer's `main_trainer`.
- **A trainee logs a measurement** — `/measurements/add/`, optionally attaching a progress
  photo. Photos are stored in Vercel Blob (see §7); trainers view them on
  `/measurements/detail/<id>/` and side-by-side on `/trainee/<id>/photos/`.
- **Charts** — `/measurements/charts/<user_id>/` renders weight/measurement history for a
  trainee, visible to that trainee and to their trainer(s).
- **Goals** — a trainee sets goals at `/goals/add/` and toggles completion from
  `/goals/`; visible to the trainee and their trainer(s).
- **Chat** — `/chat/<user_id>/`, between a trainee and any of their assigned trainers, or
  between a trainer and their helper trainers.

## 4. Bootstrapping a new deployment

A fresh deployment starts with zero users, so nobody can log in to use the in-app
"add trainee"/"add trainer" forms yet. Use the `create_user` management command instead —
it talks directly to the database, not through the running app, so it works the same way
whether you point it at local SQLite or a remote production Postgres instance.

**To create the first admin against production:**

1. Pull the production `DATABASE_URL` locally — either `vercel env pull
   .env.production.local`, or copy the value from the Vercel dashboard by hand. Vercel
   Postgres is reachable directly over the network, so no shell access to the Vercel
   deployment itself is needed.
2. Run the command against that database:

   ```
   DATABASE_URL=<prod-connection-string> python manage.py create_user --role admin --username <name>
   ```

   You'll be prompted twice for a password (hidden input). This creates a Django
   superuser — log in at `/login/` and you'll be redirected straight to `/admin/`.
3. From there, either keep using `create_user` for more accounts, or use `/admin/`
   directly (it's fully wired up via `CustomUserAdmin` — you can set `role`,
   `head_trainer`, and `helpers` from the admin forms too).

The same command creates trainers and trainees, e.g.:

```
python manage.py create_user --role trainer --username coach1
python manage.py create_user --role trainee --username jana --head-trainer coach1
```

Once at least one trainer exists and can log in, day-to-day trainee/helper-trainer
creation should go through the in-app forms (`/users/add-trainee/`, `/users/add-trainer/`)
described in §3 — `create_user` exists to get *out* of the zero-users bootstrap problem,
not to replace those flows.

## 5. `create_user` reference

```
python manage.py create_user --role {admin,trainer,trainee} --username NAME
    [--email EMAIL] [--password PASSWORD] [--head-trainer TRAINER_USERNAME]
```

- `--role` — required; one of `admin`, `trainer`, `trainee`.
- `--username` — required; the command fails loudly (no changes made) if that username
  already exists.
- `--email` — optional, defaults to blank.
- `--password` — optional. If omitted, you're prompted twice with hidden input (same as
  `createsuperuser`). Passing it directly is supported for scripted/throwaway seeding, but
  is less safe — it can land in your shell history.
- `--head-trainer` — optional, only meaningful with `--role trainee`; must name an
  existing user whose `role` is `trainer`. Ignored (with a warning) for the other roles.

## 6. Environment variables

| Variable | Purpose | Required when |
|----------|---------|----------------|
| `DATABASE_URL` | Postgres connection string (Vercel Postgres in production) | Production; unset locally falls back to `db.sqlite3` |
| `BLOB_READ_WRITE_TOKEN` | Vercel Blob read/write token, used by the photo storage backend (`core/storage.py`) | Any time a progress photo is uploaded or served |
| `VERCEL_BLOB_BASE_URL` | Override the public Blob host if it can't be derived from the token | Only as a fallback |
| `SECRET_KEY` | Django secret key | Always in production (defaults to a dev-only value locally) |
| `DEBUG` | `"True"`/`"False"` | Always set explicitly in production (`"False"`) |
| `ALLOWED_HOSTS` | Comma-separated allowed hostnames | Production, if the default (`.vercel.app,localhost,127.0.0.1`) doesn't cover your domain |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins for CSRF (POST forms, e.g. login) | Production, if the default (`https://*.vercel.app`) doesn't cover your domain |

## 7. Known limitations

- `core/urls.py` defines the `compare_photos` route twice (harmless — Django just uses
  the last one) — pre-existing, not touched by this manual's changes.
- `trener_app/urls.py` references `settings.MEDIA_URL`/`MEDIA_ROOT` in `DEBUG` mode, but
  neither is defined in `settings.py` (photo storage lives in Vercel Blob, not local
  media) — pre-existing, harmless in practice since it's dead code under the current
  storage backend, but worth knowing about if you see it while reading `urls.py`.
