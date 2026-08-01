# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Streamlit app ("Clinical Consultation Analyzer") that extracts medical symptoms and diagnoses
from clinical consultation notes using an LLM (via the `langextract` library), lets a user
review/edit the extracted results, and exports them as a JSON entities/relationships payload for
Neo4j ingestion. The entire app is one file: `streamlit_app.py`.

This used to be a two-service app (FastAPI backend + React frontend); that was replaced with a
single Streamlit app to simplify local prototyping. There is no backend/frontend split anymore —
don't reintroduce one without discussing it first.

## Commands

```bash
pip install -r requirements-streamlit.txt   # install deps
streamlit run streamlit_app.py              # run the app (http://localhost:8501)
python3 -m py_compile streamlit_app.py      # quick syntax check
```

There is no automated test suite or linter configured for this project. Verify changes by running
the app and exercising the flow in the browser.

Requires a `.env` file at the project root (see `.env.example`) with `LANGEXTRACT_API_KEY` set.
The app calls `load_dotenv()` against the project root on startup, then again against
`backend/.env` (`override=False`) — a fallback from the old FastAPI-backend layout. There is no
`backend/` directory anymore, so that second call is currently a no-op; it's harmless but stale.

## Architecture

Everything lives in `streamlit_app.py`, structured as:

- **Extraction config** — two prompt/few-shot-example pairs passed to `langextract`:
  `EXTRACTION_PROMPT`/`EXTRACTION_EXAMPLES` for symptoms, and
  `DIAGNOSIS_EXTRACTION_PROMPT`/`DIAGNOSIS_EXTRACTION_EXAMPLES` for diagnoses (the latter mirrors
  the `status`/`certainty` enums on the `Diagnosis` entity in `schema.json`). Both extractions run
  against a single input field rather than the combined consultation text: symptoms against
  History only, diagnoses against Diagnosis only. Symptom extraction is normalized: the prompt
  instructs the LLM to extract only the canonical symptom name (`"cough"`, not `"productive cough
  with green sputum"`) as `extraction_text`, pushing qualifying detail not already captured by
  `body_part`/`severity`/`duration` into a `descriptor` attribute instead — this keeps the
  `Presentation` node's `text` consistent across consultations that describe the same symptom
  differently, rather than producing a different-looking node per phrasing. `descriptor` isn't a
  property `schema.json` defines on `Presentation` (only `name`/`severity`/`duration` are), same
  as the pre-existing `body_part` attribute — extra properties pass through unvalidated. If
  extraction quality needs tuning, this is where it happens.
- **`run_extraction(text, model_id, prompt, examples)`** — calls `lx.extract(...)` and normalizes
  the result into a list of `{text, attributes, position}` dicts. `position` holds character
  offsets (`char_interval.start_pos`/`end_pos`) into the original text, used later for source
  highlighting. Generalized over `prompt`/`examples` so it's reused for both the symptom and
  diagnosis passes.
- **`build_entities_payload(symptoms, diagnoses, encounter_datetime, clinical_notes)`** /
  **`_to_entity(...)`** — format symptoms and diagnoses into a JSON `{entities, relationships}`
  payload matching the Entity/Relationship contract used by the separate `cliniprompt-graph`
  project's Neo4j ingestion. Entity `type` values (`"Encounter"`, `"Presentation"`, `"Diagnosis"`)
  are `schema.json` entity labels used directly as Neo4j node labels there, so they must stay
  capitalized exactly as in `schema.json`. Every payload has exactly one `Encounter` entity
  (id `"encounter-1"`) acting as the anchor node — its `encounter_date` property is captured as
  `datetime.now()` at the moment "Analyse" is clicked (stored in
  `st.session_state.encounter_datetime`), and its `clinical_notes` property is the combined
  History/Examination/Diagnosis/Plan text (`st.session_state.original_text`), matching
  `schema.json`'s description of that field. Each Presentation/Diagnosis entity gets a
  corresponding `PRESENTED_WITH`/`DIAGNOSED_WITH` relationship from the encounter, per
  `schema.json`'s relationship definitions. There's still no Patient/Clinician/Facility wrapper —
  this app doesn't collect that metadata — and the app only populates the Encounter properties it
  actually collects (`encounter_date`, `clinical_notes`); other schema-defined Encounter
  properties (`encounter_type`, `chief_complaint`, `duration_minutes`, `outcome`) are omitted
  rather than guessed at.
- **`get_source_context(symptom, original_text, padding=100)`** — reconstructs a highlighted
  snippet around an item's position for the "view source" (📍) toggle, entirely client-side
  from the stored offsets — there's no server-rendered HTML view like the old FastAPI
  `/visualize` endpoint had. Used by both the symptoms and diagnoses panels.
- **`render_results_panel(...)`** — renders one results panel (list + 📍/✕ controls + "add new"
  form); parameterized by session-state keys and labels so it's reused for both the Symptoms and
  Diagnoses tabs rather than duplicated.
- **UI section** (bottom of the file) — three-column layout (History/Examination/Diagnosis/Plan
  inputs → Analyse button → tabbed results panel with separate Symptoms and Diagnoses tabs). All
  app state (`symptoms`, `original_text`, `symptom_source_text`, `symptom_expanded_index`,
  `diagnoses`, `diagnosis_source_text`, `diagnosis_expanded_index`, `error`, `encounter_datetime`)
  lives in `st.session_state`, which is scoped per browser session. `original_text` (the combined
  History/Examination/Diagnosis/Plan text) is kept only for the Encounter's `clinical_notes`
  property — `symptom_source_text` (History only) and `diagnosis_source_text` (Diagnosis only) are
  what each results panel's "view source" (📍) highlighting is actually reconstructed from, so
  offsets line up with the field each extraction pass ran against. This was a deliberate fix for a
  bug in the old FastAPI backend, which stored the last extraction result as attributes on the global
  `app` object — safe for one user, broken for concurrent ones. Don't reintroduce
  module-level/global mutable state for request data.
- **`SAMPLE_CASES`** / sidebar loader — a dict of sample case name → `{history, examination,
  diagnosis, plan}` text. The sidebar (`st.sidebar`, rendered right after the API-key check) has a
  selectbox over `SAMPLE_CASES` and a "Load Sample Case" button that writes the chosen case's
  fields directly into `st.session_state.history`/`.examination`/`.diagnosis`/`.plan` (the same
  keys the four `text_area` widgets use) before calling `st.rerun()`. This relies on the sidebar
  block executing *before* the `text_area` widgets are instantiated later in the script — Streamlit
  requires a widget's session-state value to be set before that widget is created on the same run,
  so don't move this block below the `left, center, right` columns or the load will silently no-op
  on the next widget instantiation.

Symptoms and diagnoses can each be added manually (via a form) or removed, independent of
extraction — the lists in `st.session_state.symptoms`/`st.session_state.diagnoses` are the single
source of truth once populated, not re-derived from the LLM result after edits.

The default `model_id` is `"gemini-3.6-flash"`, exposed as an editable field in the UI (not
hardcoded) because it doesn't match the vendored `langextract` library's documented default of
`gemini-3.5-flash` — this was never fully verified against the active API key/provider.

`REQUEST_GUIDE.md` documents Gemini free-tier rate limits (20 RPM / 300 QPD) and how
`extraction_passes`, `max_workers`, and `max_char_buffer` affect request volume — relevant if
`run_extraction` is ever changed to process multiple documents or use more than one pass.

## Repo layout gotcha: `graphgen/` is a separate git repository

`graphgen/` is a full local clone of the user's fork of Google's `langextract` library (the core
dependency of this app), kept around for reference. It has its own `.git`, its own GitHub remote,
and its own branch (`main`) — it is **not** part of this app's source and should not be edited or
committed to as part of app changes.

Confusingly, its remote (`https://github.com/jjroberts88/graphgen`) is the **same GitHub repo** as
this project's remote — they're just different branches of one repo: this app lives on `master`,
the langextract fork lives on `main`. They don't affect each other when pushing to their own
branch, but:

- Always check `pwd` and `git status` (which repo/branch) before running git commands — `cd`-ing
  into `graphgen/` and forgetting to `cd` back has caused a misdirected push attempt before.
- Run git commands for this app from the project root, not from inside `graphgen/`.
