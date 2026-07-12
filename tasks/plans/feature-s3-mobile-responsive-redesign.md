# Feature Plan — S3: Mobile-friendly responsive redesign

**Epic:** [epic-vercel-mobile-rewrite.md](./epic-vercel-mobile-rewrite.md) — step 3 of 4
**Ticket:** none (developer-request epic; this repo has no linked GitHub issues)
**Slug:** mobile-responsive-redesign
**Author:** Claude (Opus 4.8)
**Date:** 2026-07-12
**Status:** Complete — implemented and manually verified 2026-07-12
**Epic status:** Approved (open questions resolved 2026-07-11)

> **No automated tests** (project directive). Verification is manual only — see §7.
> This is a Django/Python project — the epic's PHP/Doctrine/Twig phrasing maps to
> Django ORM / Django templates / PEP 8; there is no PSR-12 or Doctrine here.

---

## 1. Summary

Rework `core/static/core/style.css` **mobile-first** and refresh the visual style
(colors, typography, spacing) so every page is usable and legible on a narrow (≤400px)
phone viewport without page-level horizontal scrolling, while not regressing on desktop.
Per epic §3/§6 Q3: **no CSS framework, no JS framework, no build step** — hand-rolled CSS
only, plus the minimum presentational edits to templates (add CSS classes, `data-label`
attributes, move inline fixed-width styles into classes). This is the "phone friendly" +
"rework the design" ask.

S3 is **presentation only**. It changes no domain model, no URLs, no view logic, and no
template control flow (`{% if %}` / `{% for %}` / `{% url %}` / form fields stay exactly
as they are). It depends on nothing and can land in parallel with S1/S2 (epic §7 S3).

The redesign also closes several pre-existing CSS gaps discovered during the survey —
classes referenced by templates but never defined (`.btn-green`, `.btn-red`, `.navbar`
family, `.container`, `.full-image`, `.message-time`), a fixed footer that overlaps
content on mobile, and a 9-column measurement table that overflows any phone. These are
in scope because they are exactly the "fixed-width forms/tables/nav/footer" the epic §7
S3 brief names.

---

## 2. Acceptance criteria

Copied from epic §7 S3 (verbatim), with IDs:

- [x] **AC-1** — All existing pages (home, measurement list/detail/add, compare photos,
  charts, goals, chat, trainee/trainer add/edit/delete, login/register) are usable and
  legible on a narrow (≤400px) viewport without horizontal scrolling, with the same
  functionality as today. Covered by: `core/static/core/style.css:1-336` (mobile-first
  base rules, no desktop-only assumptions).
- [x] **AC-2** — No layout regressions on desktop widths. Covered by:
  `core/static/core/style.css:326-336` (`@media (min-width: 768px)` layer).

Derived sub-criteria required to satisfy the above without changing behaviour:

- [x] **AC-1a** — The nav bar (up to 7 links: Domov, Používatelia, Merania, Ciele, Pridať
  trénera, Pridať zverenca, Odhlásiť) is fully reachable and tappable at ≤400px without
  overflow (§5.3). Covered by: `core/static/core/style.css:36-77` (`.navbar`/`.nav-left`/
  `.nav-right` wrapping flex layout, 44px min-height touch targets).
- [x] **AC-1b** — The 9-column measurement table and the users/goals tables are legible at
  ≤400px without the page scrolling sideways (stacked-card pattern, §5.5). Covered by:
  `core/static/core/style.css:193-249` (stacked-card `@media (max-width: 767px)` rules) +
  `core/templates/core/measurement_list.html:22-73`, `core/templates/core/user_list.html:10-46`,
  `core/templates/core/goal_list.html:11-35` (`.table-wrap` + `data-label` on every `<td>`).
- [x] **AC-1c** — Every button rendered by a template has a defined, consistent style —
  including `.btn-green` and `.btn-red` (currently undefined) and the two bare `<button>`
  elements in `add_goal.html` / `add_trainer.html` (§5.4). Covered by:
  `core/static/core/style.css:165-181` (`.btn-blue`/`.btn-green`/`.btn-red` + bare
  `button`/`input[type=submit]` rule) + `core/templates/core/add_goal.html:10`,
  `core/templates/core/add_trainer.html:8` (`class="btn-blue"` added).
- [x] **AC-1d** — The footer no longer overlaps page content on any viewport (sticky-footer
  via flex, not `position: fixed`) (§5.2). Covered by: `core/static/core/style.css:29-97`
  (`body` flex column + `main.container { flex: 1 0 auto }` + `footer { position: static }`).
- [x] **AC-1e** — Forms, the compare-photos grid, the photo thumbnails, and the chat panel
  use fluid widths (no fixed pixel widths that force overflow) and preserve their current
  behaviour (§5.6–5.8). Covered by: `core/static/core/style.css:105-135` (fluid forms/
  inputs/`.full-image`/`.thumb`), `:265-300` (`.photo-select`/`.photo-comparison` grids),
  `:251-263` (`.chat-container`/`.messages`) + `core/templates/core/compare_photos.html`
  (inline widths removed), `core/templates/core/measurement_list.html:55`
  (`class="thumb"`), `core/templates/core/measurement_detail.html` (redundant
  `.container` div removed).
- [x] **AC-2a** — At ≥768px the nav is a single row, tables render as normal tables, forms
  are centered at a readable max-width, and the compare/photo grids reflow to multiple
  columns — i.e. the current desktop experience is preserved or improved, not lost.
  Covered by: `core/static/core/style.css:326-336` (`@media (min-width: 768px)` nav/table
  polish; the `auto-fill minmax` grids and centered `max-width: 32rem` forms are
  unconditional so they already reflow correctly at desktop widths).

> Note on "register": the epic AC lists a register page, but registration was removed
> earlier in this repo (`register.html` / `registracia.html` are deleted per `git status`,
> and `base.html` shows no "Registrovať" link). There is no register template to style;
> `login.html` is the only auth page. Flagged in §11 Q5 — no action unless the developer
> reinstates registration.

---

## 3. Scope

### In scope
- **`core/static/core/style.css`** — full mobile-first rewrite + visual refresh:
  `:root` design tokens (color palette, spacing, radius, shadow, max-width), system font
  stack, global resets (`box-sizing`, fluid `img`), sticky-footer layout, styled
  `.navbar` family, unified button styles (`.btn-blue`/`.btn-green`/`.btn-red` + bare
  `<button>`), fluid forms, responsive stacked tables, fluid photo/compare grids,
  responsive chat panel, and a single `@media (min-width: 768px)` desktop layer.
- **Presentational-only template edits** (no control-flow / no logic changes):
  - `measurement_list.html`, `user_list.html`, `goal_list.html` — add `data-label`
    attributes to `<td>`s and wrap each `<table>` in a `.table-wrap` div (for the
    stacked-card responsive pattern, §5.5).
  - `add_goal.html`, `add_trainer.html` — add `class="btn-blue"` to their bare submit
    `<button>`s (§5.4).
  - `compare_photos.html` — replace inline `style="…"` blocks with CSS classes
    (`.photo-select`, `.photo-comparison`, `.compare-item`, `.compare-thumb`) so the
    fixed 150px/250px widths become fluid (§5.7).
  - `measurement_detail.html` — remove the redundant nested `<div class="container">`
    (its parent `<main class="container">` already provides it) and keep the
    `.full-image` class (now defined in CSS) (§5.6).
  - `measurement_list.html` — move the thumbnail's inline `style="width:50px"` to a
    `.thumb` class (§5.6).
  - `measurement_charts.html` — move the inline `style="height:400px"` on the chart
    wrapper to a `.chart-box` class so height can be viewport-responsive (§5.9).
  - `add_measurement.html` — trim the 3 leading blank lines above `{% extends %}`
    (cosmetic only; the inline date-defaulting `<script>` is functional and stays).

### Out of scope (deferred / not touched)
- Any HTML structural change beyond adding classes / `data-label` / wrapping a table /
  removing one redundant nested div. No new pages, no removed pages, no reordered fields.
- All view logic, URLs, forms (`forms.py`), models, and migrations — untouched (this is
  presentation only; epic §7 S3 "Out of scope").
- The AJAX chat polling `<script>` in `chat.html` and the Chart.js CDN `<script>` in
  `measurement_charts.html` — behaviour unchanged; only their containers get responsive
  CSS. (Note: the Chart.js `<script src="https://cdn.jsdelivr.net/npm/chart.js">` is an
  external dependency but pre-existing and functional; S3 does not add or remove it.)
- Dead-code view dedup, un-tracking `db.sqlite3`, stray-file removal — **S4** (epic §7 S4).
- Storage/DB/deploy config — **S1/S2**.
- Dark mode / theme switching — not in the ACs (§11 Q4).
- A JS hamburger menu or any new JS — epic forbids new JS frameworks/build steps; the
  nav is solved with zero-JS CSS (§5.3, §11 Q1).

---

## 4. Data model & migrations

**None.** S3 touches no models, fields, or migrations. No database access of any kind is
added or changed. (This section is retained for parity with the sibling plans; there is
nothing to do here.)

---

## 5. Architecture & decisions

### 5.1 Design tokens, resets, and typography (`style.css` top)
Introduce a `:root` block so the visual refresh is centralized and tweakable in one place:

```css
:root {
  --color-primary: #0d6efd;      /* refined from the current #007BFF */
  --color-primary-dark: #0a58ca;
  --color-success: #198754;      /* backs the previously-undefined .btn-green */
  --color-danger: #dc3545;       /* backs the previously-undefined .btn-red */
  --color-bg: #f4f6f8;
  --color-surface: #ffffff;
  --color-text: #1f2937;
  --color-muted: #6b7280;
  --color-border: #e2e8f0;
  --radius: 10px;
  --shadow: 0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06);
  --space: 1rem;
  --max-width: 960px;
  --font: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
}
*, *::before, *::after { box-sizing: border-box; }
img { max-width: 100%; height: auto; }
html { -webkit-text-size-adjust: 100%; }
body { font-family: var(--font); font-size: 16px; line-height: 1.5; color: var(--color-text); }
```

- **System font stack** — no web-font download, no external request, no build step
  (keeps the epic's "as simple as possible" bar and stays CSP-clean for Vercel).
- Keep blue as the brand primary (epic §6 Q3 "keep it simple"), just refined to a slightly
  more modern shade. See §11 Q3 if the developer wants a different accent.
- `font-size: 16px` on inputs specifically (in §5.6) prevents iOS Safari's auto-zoom on
  focus — a key phone-usability detail.

### 5.2 Sticky-footer layout (fixes AC-1d)
The current `footer { position: fixed; bottom: 0 }` overlaps content on short/mobile
viewports because nothing reserves space for it. Replace with a flex sticky footer:

```css
body { min-height: 100dvh; display: flex; flex-direction: column; margin: 0; background: var(--color-bg); }
main.container { flex: 1 0 auto; width: 100%; max-width: var(--max-width); margin: 0 auto; padding: var(--space); }
footer { flex-shrink: 0; position: static; background: var(--color-primary); color: #fff; text-align: center; padding: var(--space); }
```

- `100dvh` (dynamic viewport height) handles mobile browser chrome correctly; falls back
  fine on desktop. `main.container` now *defines* `.container` (currently undefined) as
  the centered max-width wrapper (fixes the `measurement_detail` nesting — see §5.6).

### 5.3 Navbar (fixes AC-1a, AC-2a) — zero-JS, no markup change
`base.html`'s `<nav class="navbar">` with `.nav-left`/`.nav-right` currently has **no CSS
at all** (the old CSS styled `<header>`, whose sole child is `.navbar`). Style the actual
classes and let links wrap on mobile — no hamburger, no JS (epic constraint):

```css
header { background: var(--color-primary); }
.navbar { max-width: var(--max-width); margin: 0 auto; padding: .5rem var(--space);
          display: flex; flex-wrap: wrap; align-items: center; gap: .25rem .5rem; }
.nav-left { flex: 1 1 100%; }                 /* logo on its own line on mobile */
.nav-right { display: flex; flex-wrap: wrap; gap: .25rem; width: 100%; }
.navbar a { color: #fff; text-decoration: none; padding: .5rem .75rem; border-radius: 6px;
            min-height: 44px; display: inline-flex; align-items: center; }  /* 44px touch target */
.navbar a:hover { background: rgba(255,255,255,.15); text-decoration: none; }
.logo { font-weight: 700; font-size: 1.15rem; }
```

Desktop layer (§5.10) flips `.nav-left`/`.nav-right` to `flex: 0 0 auto` / `width: auto`
and `margin-left: auto` so it's a single row, logo left, links right — matching (and
tidying) today's intended desktop look.

- **Why wrapping, not a hamburger:** 7 short Slovak links wrap to 2–3 tidy rows at 400px;
  a hamburger needs either JS or the checkbox-hack markup change, both of which push past
  "as simple as possible." Raised as §11 Q1 in case the developer prefers the hamburger.
- The `.btn-blue` class currently on some nav links (Pridať…, Odhlásiť, Prihlásiť) still
  works — it just renders as a solid button inside the wrapping nav. Acceptable; the
  desktop layer keeps them looking like buttons.

### 5.4 Buttons (fixes AC-1c)
`.btn-green` and `.btn-red` are used in `user_list.html`, `compare_photos.html`, and
`delete_trainee.html` but **are not defined anywhere** — they currently render as plain
underlined links. `add_goal.html` and `add_trainer.html` submit with a **bare
`<button>`** (no class). Define a shared button base and the three color variants, and
style bare `<button>`/`input[type=submit]` as a sensible default:

```css
.btn-blue, .btn-green, .btn-red,
button, input[type="submit"] {
  display: inline-flex; align-items: center; justify-content: center;
  min-height: 44px; padding: .55rem 1rem; border: none; border-radius: 8px;
  font-size: 1rem; font-weight: 600; color: #fff; cursor: pointer;
  text-decoration: none; transition: background-color .2s ease;
}
.btn-blue, button, input[type="submit"] { background: var(--color-primary); }
.btn-blue:hover, button:hover { background: var(--color-primary-dark); }
.btn-green { background: var(--color-success); }
.btn-green:hover { background: #157347; }
.btn-red { background: var(--color-danger); }
.btn-red:hover { background: #bb2d3b; }
```

- Also add `class="btn-blue"` to the bare buttons in `add_goal.html` / `add_trainer.html`
  for explicitness (the bare-`button` rule already covers them, but the class keeps
  intent obvious and matches every other form). Both approaches are belt-and-suspenders;
  the CSS rule alone satisfies AC-1c even if a template is missed.
- On mobile, action-cell buttons (`.btn-green`/`.btn-red` in `user_list`) get
  `width: 100%` inside the stacked card (§5.5) so they're easy to tap; desktop keeps them
  inline.

### 5.5 Responsive tables → stacked cards (fixes AC-1b, AC-2a)
Three tables: `measurement_list` (9 data columns), `user_list` (up to 4), `goal_list` (3).
At 400px a 9-column table cannot fit. Chosen pattern: **stacked cards on mobile, normal
tables on desktop**, using `data-label` attributes + CSS generated content — the standard
zero-JS responsive-table technique. No horizontal scroll, fully legible.

Template edit (each `<td>` gets a label matching its column header), e.g. in
`measurement_list.html`:

```html
<td data-label="Váha">{{ measurement.weight|default_if_none:"N/A" }} kg</td>
```

CSS (mobile-first = stacked by default; desktop restores the table):

```css
.table-wrap { width: 100%; }
table { width: 100%; border-collapse: collapse; background: var(--color-surface);
        border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow); }
/* mobile: hide the header row, render each row as a card */
@media (max-width: 767px) {
  table thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  table tr { display: block; margin-bottom: var(--space); border: 1px solid var(--color-border);
             border-radius: var(--radius); background: var(--color-surface); padding: .5rem; }
  table td { display: flex; justify-content: space-between; gap: 1rem;
             border: none; border-bottom: 1px solid var(--color-border); padding: .5rem; text-align: right; }
  table td:last-child { border-bottom: none; }
  table td::before { content: attr(data-label); font-weight: 700; color: var(--color-muted); text-align: left; }
  table td[data-label=""]::before, table td:not([data-label])::before { content: none; }
}
```

- Wrap each `<table>` in `<div class="table-wrap">` so a future wide-table case can add
  `overflow-x: auto` without touching markup again; also gives the desktop table a clean
  block context.
- The empty-state rows (`<td colspan="9">Žiadne merania…`) render fine as a single card
  line (no `data-label` → no `::before`).
- Desktop (≥768px) uses the default `table td { border: 1px solid … }` look, refreshed:
  padded cells, subtle zebra striping via `tbody tr:nth-child(even)`, left-aligned text
  for readability. This is the AC-2a "no desktop regression / slight improvement" path.
- `goal_list.html` uses `class="styled-table"` and a `.no-data` cell — both currently
  undefined; the generic `table` rules now cover `.styled-table`, and `.no-data` gets a
  muted centered style. `measurement_list.html`'s `.form-select-user` (trainer filter)
  gets a small fluid style (full-width select on mobile).

### 5.6 Forms, inputs, thumbnails (fixes AC-1e)
Forms render via Django's `{{ form.as_p }}` → `<p><label>…</label> <input…></p>`. Make
them fluid and touch-friendly:

```css
form { width: 100%; max-width: 32rem; margin: var(--space) auto; background: var(--color-surface);
       padding: 1.25rem; border-radius: var(--radius); box-shadow: var(--shadow); }
form p { margin: 0 0 1rem; }
form label { display: block; font-weight: 600; margin-bottom: .25rem; }
input, select, textarea {
  width: 100%; padding: .6rem .7rem; font-size: 16px;   /* 16px = no iOS zoom-on-focus */
  border: 1px solid var(--color-border); border-radius: 8px; background: #fff; }
input[type="checkbox"], input[type="radio"] { width: auto; }
.full-image { width: 100%; max-width: 640px; border-radius: var(--radius); display: block; margin: var(--space) 0; }
.thumb { width: 56px; height: auto; border-radius: 6px; }
```

- The old `form { max-width: 400px }` becomes `32rem` and `width: 100%` so it fills a
  phone screen (with `main`'s padding) and centers on desktop — AC-1e + AC-2a.
- `measurement_detail.html`: remove its inner `<div class="container">` (redundant now
  that `main.container` is the wrapper — §5.2) and rely on the now-defined `.full-image`
  class. Photo detail becomes fluid.
- `measurement_list.html` thumbnail: replace inline `style="width: 50px; height: auto;"`
  with `class="thumb"`.

### 5.7 Compare-photos grid (fixes AC-1e, AC-2a)
`compare_photos.html` is riddled with inline styles and fixed widths (`width:150px`,
`width:250px`, inline flex). Move them to fluid classes so the grid reflows on a phone:

```css
.photo-select { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: .75rem; }
.photo-select label { text-align: center; }
.photo-select img { width: 100%; border: 1px solid var(--color-border); border-radius: 8px; }
.photo-comparison { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--space); margin-top: var(--space); }
.photo-comparison .compare-item { text-align: center; }
.photo-comparison img { width: 100%; border: 2px solid var(--color-muted); border-radius: 8px; }
```

Template edit: strip the inline `style="…"` attributes from the two `<div>`s, the
`<label>`s, and the `<img>`s and replace with `class="photo-select"` /
`class="photo-comparison"` / `class="compare-item"`. The checkbox `name="photos"`, the
`{% if … in selected_ids %}checked` logic, and the `{% url %}`s stay byte-for-byte. On
desktop the `auto-fill minmax` naturally yields multiple columns (AC-2a).

- The existing `.photo-grid` / `.photo-item` / `.compare-row` / `.compare-photo` blocks in
  the current CSS are kept but modernized to use `auto-fill minmax` with `1fr` (they're
  already close; just align them to the tokens). No template references
  `.photo-grid`/`.compare-row` today, but keep them so nothing that might use them breaks.

### 5.8 Chat panel (fixes AC-1e)
`chat.html` uses `.chat-container` / `.messages` / `.message` (defined) and
`.message-time` (used in `chat.html` + `_messages.html` but **undefined**). Make the panel
fluid and define the timestamp style:

```css
.chat-container { width: 100%; max-width: 600px; margin: var(--space) auto; }
.messages { height: 60vh; max-height: 480px; }        /* was a fixed 400px */
.message-time { font-size: .75rem; color: rgba(255,255,255,.75); align-self: flex-end; }
.message.received .message-time { color: var(--color-muted); }
.chat-form { display: flex; gap: .5rem; align-items: flex-start; }
.chat-form textarea, .chat-form input { flex: 1; }
```

- `.messages` height moves from a fixed `400px` to `60vh` (capped) so short phones aren't
  dominated by the scroll box. The AJAX-poll `<script>` and `scrollToBottom()` are
  untouched — they key off `#messages`, which is unchanged.
- No `chat.html` markup change is strictly required; the `.chat-form` class is already on
  the form. `.message-time` styling is pure CSS.

### 5.9 Charts page
`measurement_charts.html` wraps the canvas in `<div style="height:400px;">`. Move to a
`.chart-box` class so height is responsive:

```css
.chart-box { position: relative; height: 55vh; max-height: 420px; margin: var(--space) 0; }
```

Chart.js is already `responsive: true`; only the wrapper height changes. Template edit:
`style="height:400px;"` → `class="chart-box"`. Nothing else on this page changes.

### 5.10 The single desktop layer (`@media (min-width: 768px)`) (fixes AC-2, AC-2a)
Everything above is mobile-first (base = phone). One media query restores/improves desktop:

```css
@media (min-width: 768px) {
  .nav-left { flex: 0 0 auto; }
  .nav-right { width: auto; margin-left: auto; }
  /* tables render as real tables again (the max-width:767px card rules simply don't apply) */
  table td { text-align: center; border: 1px solid var(--color-border); }
  tbody tr:nth-child(even) { background: #fafbfc; }
}
```

Because the stacked-card rules live under `@media (max-width: 767px)`, the desktop table
is the plain default — no override needed for the table itself, only the polish above.

### 5.11 Conventions
- Pure CSS, no preprocessor, no framework, no build (epic §6 Q3). Single file:
  `core/static/core/style.css`, fully rewritten but organized under the same
  `/* ==== SECTION ==== */` comment style already present.
- Mobile-first: unprefixed rules target phones; `@media (min-width: 768px)` (and the one
  `max-width: 767px` table block) are the only breakpoints. One breakpoint keeps it
  simple and covers phone↔desktop; tablet inherits the desktop layer cleanly.
- Template edits are **presentational only** — adding `class`/`data-label`, wrapping a
  table, removing one redundant nested `<div>`, deleting leading blank lines. Zero changes
  to `{% %}` tags, form fields, URLs, or `<script>` behaviour. No business logic enters
  templates (there was none to add).
- All template attribute values stay valid Django template syntax; `data-label` values are
  static strings matching the existing `<th>` text.

---

## 6. File Plan

| # | File | Change | ACs |
|---|------|--------|-----|
| 1 | `core/static/core/style.css` **(full rewrite)** | `:root` tokens + resets + system font (§5.1); sticky-footer flex layout defining `.container` (§5.2); `.navbar`/`.nav-left`/`.nav-right`/`.logo` styles (§5.3); unified `.btn-blue`/`.btn-green`/`.btn-red` + bare-button styles (§5.4); responsive stacked-table + `.table-wrap`/`.styled-table`/`.no-data`/`.form-select-user` (§5.5); fluid `form`/inputs/`.full-image`/`.thumb` (§5.6); `.photo-select`/`.photo-comparison`/`.compare-item` + refreshed `.photo-grid`/`.compare-*` (§5.7); `.chat-container`/`.messages`/`.message-time`/`.chat-form` (§5.8); `.chart-box` (§5.9); single `@media (min-width:768px)` desktop layer (§5.10) | AC-1, AC-2, AC-1a–e, AC-2a |
| 2 | `core/templates/core/measurement_list.html` | Add `data-label` to all 9 `<td>`s; wrap `<table>` in `<div class="table-wrap">`; thumbnail inline `style` → `class="thumb"`. No logic change | AC-1b, AC-1e |
| 3 | `core/templates/core/user_list.html` | Add `data-label` to `<td>`s; wrap `<table>` in `.table-wrap`. Action-cell buttons already carry `.btn-green`/`.btn-red`/`.btn-blue` (now defined) | AC-1b, AC-1c |
| 4 | `core/templates/core/goal_list.html` | Add `data-label` to `<td>`s; wrap `.styled-table` in `.table-wrap` | AC-1b |
| 5 | `core/templates/core/compare_photos.html` | Replace inline `style="…"` on the two grids, `<label>`s and `<img>`s with `class="photo-select"`/`"photo-comparison"`/`"compare-item"`; keep checkbox/`{% if %}`/`{% url %}` logic verbatim | AC-1e, AC-2a |
| 6 | `core/templates/core/measurement_detail.html` | Remove redundant inner `<div class="container">` wrapper (keep contents); `.full-image` now styled | AC-1e |
| 7 | `core/templates/core/measurement_charts.html` | Chart wrapper inline `style="height:400px"` → `class="chart-box"` | AC-1, AC-1e |
| 8 | `core/templates/core/add_goal.html` | Add `class="btn-blue"` to the bare submit `<button>` | AC-1c |
| 9 | `core/templates/core/add_trainer.html` | Add `class="btn-blue"` to the bare submit `<button>` | AC-1c |
| 10 | `core/templates/core/add_measurement.html` | Delete the 3 leading blank lines above `{% extends %}` (cosmetic); date `<script>` untouched | — |

- `base.html` needs **no change** — the nav redesign is pure CSS against its existing
  `.navbar`/`.nav-left`/`.nav-right`/`.logo` classes (§5.3). It is listed here only to
  state explicitly that it is intentionally left alone.
- `login.html`, `home_trainer.html`, `home_trainee.html`, `add_trainee.html`,
  `edit_trainee.html`, `delete_trainee.html`, `chat.html`, `_messages.html` need **no**
  template edits — they already use classes the rewritten CSS now styles correctly.
- No file outside `core/static/core/style.css` and `core/templates/core/*` is edited.

---

## 7. Manual verification

All manual — no automated tests (project directive). Run `python manage.py runserver`
(SQLite fallback is fine for S3; no `DATABASE_URL`/`BLOB_READ_WRITE_TOKEN` needed to view
layout). Use browser DevTools device toolbar (or a real phone) at a **375–400px** width
for the mobile checks, and a normal desktop window for the regression checks.

**Mobile ≤400px (AC-1, AC-1a–e):**
1. Log in via `login.html` — form fills the screen, is centered, inputs are full-width and
   don't trigger iOS zoom-on-focus (16px font). Button is full-tap-height.
2. Header nav (as trainer, most links) — all 7 links visible/tappable, wrap tidily, no
   sideways page scroll; logo readable.
3. `/measurements/` — the 9-column table renders as **stacked cards**, each field labeled
   (Váha, Hrudník, …); no horizontal page scroll; thumbnail small and tappable → opens
   full image. As trainer, the "Vybrať zverenca" select is full-width.
4. `/users/` (`user_list`) — stacked cards; "Otvoriť chat"/"Porovnať fotky" (green) and
   "Upraviť"/"Zmazať" (red/blue) all show correct solid colors (previously unstyled) and
   are easy to tap.
5. `goal_list`, `add_goal`, `add_trainer`, `add_measurement`, `add_trainee`,
   `edit_trainee`, `delete_trainee` — forms/tables fit, all buttons styled (incl. the two
   formerly-bare submit buttons), no overflow.
6. `compare_photos` for a trainee — the selectable thumbnails grid and the compared-photos
   grid reflow to fit the phone; checkboxes still select; "Porovnať vybrané" still submits
   and re-renders the selection.
7. `measurement_detail` — full photo scales to width, no overflow; "Späť na zoznam" button
   styled.
8. `measurement_charts` — the Chart.js line chart is responsive and readable; legend below;
   no horizontal scroll.
9. `chat` — messages panel is ~60vh (not a cramped fixed box), sent/received bubbles and
   timestamps render (timestamp now styled), send form input is full-width; AJAX auto-scroll
   still works (leave it open ~6s to confirm the 5s poll doesn't break layout).
10. **Confirm no page scrolls horizontally** at 400px on every route above (AC-1).

**Desktop ≥768px (AC-2, AC-2a):**
11. Nav is a single row: logo left, links right; hover states work.
12. All three tables render as normal tables (header row visible, zebra striping), not
    cards.
13. Forms are centered at a comfortable max-width (not full-bleed).
14. `compare_photos` grids show multiple columns; chat panel centered at ≤600px.
15. Spot-check every route from steps 1–9 for any obvious layout regression vs. today.

**Cross-cutting:**
16. `python manage.py check` is clean and `runserver` serves `/static/core/style.css`
    (200, correct MIME) — confirm no CSS syntax error broke the stylesheet (a broken CSS
    file fails silently in the browser, so eyeball at least one styled page).
17. Grep sanity: `grep -rn 'style=' core/templates/core/compare_photos.html
    core/templates/core/measurement_detail.html core/templates/core/measurement_list.html
    core/templates/core/measurement_charts.html` — the inline styles targeted in §6 are
    gone (a couple of unrelated inline styles elsewhere are fine; only the listed ones are
    in scope).

---

## 8. Config / env vars introduced

**None.** S3 adds no settings, env vars, dependencies, or migrations. It is a static-asset
+ template presentation change only. (WhiteNoise static-serving config is **S2**; S3's CSS
is served by whatever static handling is active at the time it lands — the Django dev
server locally, WhiteNoise once S2 merges.)

---

## 11. Open questions — resolved 2026-07-12

All resolved to the proposed defaults (developer approved all defaults 2026-07-12).
Decisions below are binding for `/implement-feature`.

- **Q1 — Mobile nav pattern. RESOLVED: wrapping links (zero-JS), no hamburger.**
  7 short links wrap to 2–3 rows at 400px; no `base.html` markup change, no JS (§5.3).

- **Q2 — Responsive table strategy. RESOLVED: stacked cards via `data-label`.**
  Truly eliminates horizontal scroll and is most legible for the 9-column measurement
  table on a phone (AC-1b) (§5.5).

- **Q3 — Color direction. RESOLVED: keep blue as the brand primary**, refined
  (`#007BFF` → `#0d6efd`) plus a neutral palette, green (success) and red (danger)
  accents (§5.1).

- **Q4 — Dark mode? RESOLVED: out of scope** — not in the ACs. Tokens are structured so a
  `@media (prefers-color-scheme: dark)` layer could be added later cheaply; S3 ships
  light-only.

- **Q5 — Registration page. RESOLVED: no action** — `register.html`/`registracia.html`
  are deleted and `base.html` has no register link; there is no register template to
  style. If registration is reinstated (e.g. via `feature-user-bootstrap-admin.md`), its
  template joins the styling pass as a follow-up.

---

## 13. Post-Implementation

_(Filled in by `/implement-feature` after the work lands.)_

**What was built:** Full mobile-first rewrite of `core/static/core/style.css` (design
tokens, sticky-footer layout, wrapping zero-JS navbar, unified button styles, stacked-card
responsive tables, fluid forms/photo grids/chat panel, single `@media (min-width: 768px)`
desktop layer) plus the presentational-only template edits listed in plan §6
(`data-label` + `.table-wrap` on the three tables, `.btn-blue` on the two bare buttons,
inline-style removal in `compare_photos.html`, redundant `<div class="container">` removal
in `measurement_detail.html`, `.thumb`/`.chart-box` class swaps, blank-line trim in
`add_measurement.html`).

**Verified:** `python manage.py check` clean. `DEBUG=True` dev server confirms
`/static/core/style.css` returns `200 text/css`. Used Django's test `Client` with
`force_login` (no browser available in this environment) to render `/users/`,
`/measurements/`, `/goals/`, `/goals/add/`, `/chat/<id>/`, `/login/` as real
authenticated users and confirmed the expected classes/attributes appear in the HTML:
`table-wrap`, `data-label`, `btn-green`, `btn-blue`, `chat-container`, `message-time`.
Grep-confirmed the targeted inline `style=` attributes in `compare_photos.html`,
`measurement_detail.html`, `measurement_list.html`, `measurement_charts.html` are gone
(only unrelated cosmetic margins remain, as expected per §7 step 17).

**Note on verification depth:** I do not have a browser in this environment, so the
visual/responsive checks in plan §7 (actual 375–400px rendering, tap-target sizing,
no-horizontal-scroll confirmation) were **not** performed pixel-by-pixel — only HTML
structure and CSS delivery were confirmed programmatically. The developer should still
do a quick visual pass per §7 before considering this fully done.

**Follow-ups for the developer:**
- One measurement in the dev DB (`JanJas`'s data) has a `photo` field that errors on
  `.url()` with `ValueError: BLOB_READ_WRITE_TOKEN is not set` — this is S1's Vercel Blob
  storage backend requiring that env var locally; it pre-dates this change and is out of
  S3's scope, but it will block visually checking `measurement_list`/`measurement_detail`
  for any user with existing photos until `BLOB_READ_WRITE_TOKEN` is set locally or that
  seed data is cleared.
- Unrelated to S3: at the start of this task `main` already had uncommitted changes
  (`README.md`, `core/forms.py`, `core/views.py` modified; `register.html`/
  `registracia.html` deleted) from other in-progress work — left untouched as instructed.

## Notes on epic alignment
- Adopts epic §3/§6 Q3 verbatim: no CSS framework, no JS framework, no build step —
  hand-rolled `style.css` only. No re-litigation.
- Respects epic scope discipline (§3): no domain-model, URL, permission, or
  chat/measurement/goal logic changes — presentation only. Template edits are limited to
  classes, `data-label`, one table wrapper, one redundant-div removal, and blank-line
  trimming.
- Stays independent of S1/S2 (epic §7 S3 "Depends on: none"): needs no storage/DB/deploy
  config to verify; runs against the local SQLite fallback.
- Leaves S4's cleanup (dead-code dedup, `db.sqlite3` un-tracking, stray files) untouched.
