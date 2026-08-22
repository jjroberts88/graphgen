# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Streamlit app ("Clinical Consultation Analyzer") that extracts medical symptoms, diagnoses,
medications, and investigations from clinical consultation notes using an LLM (via the
`langextract` library), lets a user review/edit the extracted results, and exports them as a JSON
entities/relationships payload for Neo4j ingestion. The entire app is one file:
`streamlit_app.py`.

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

`NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD`/`NEO4J_DATABASE` are optional — without them the app
still works (extraction + JSON export), but the "Push to Neo4j" button and graph visualization
panel are disabled.

`BIOPORTAL_API_KEY` is optional — without it the app still works end to end (extraction, edit,
export, push); the "🔎 Find SNOMED code" lookup button on the Diagnoses panel just doesn't render
(gated by `enable_snomed_lookup and BIOPORTAL_API_KEY` in `render_results_panel`). Get a free key
from https://bioportal.bioontology.org/account — see the `search_snomed_bioportal` bullet below
for why BioPortal specifically.

## Architecture

Everything lives in `streamlit_app.py`, structured as:

- **Extraction config** — four prompt/few-shot-example pairs passed to `langextract`:
  `EXTRACTION_PROMPT`/`EXTRACTION_EXAMPLES` for symptoms,
  `DIAGNOSIS_EXTRACTION_PROMPT`/`DIAGNOSIS_EXTRACTION_EXAMPLES` for diagnoses (mirrors the
  `status`/`certainty` enums on the `Diagnosis` entity in `schema.json`),
  `MEDICATION_EXTRACTION_PROMPT`/`MEDICATION_EXTRACTION_EXAMPLES` for medications (attributes
  `dosage`/`route`/`duration`/`indication` mirror the properties `schema.json` defines on its
  `Prescription` entity, with `route` matching that entity's enum), and
  `PROCEDURE_EXTRACTION_PROMPT`/`PROCEDURE_EXTRACTION_EXAMPLES` for investigations (maps to
  `schema.json`'s `Procedure` entity — see the `build_entities_payload` bullet below for how the
  ordered-vs-performed distinction is handled). All four extractions run against a single input
  field rather than the combined consultation text: symptoms against History only, diagnoses
  against Diagnosis only, medications and investigations both against Plan only (two independent
  `lx.extract` calls over the same text — the investigation prompt explicitly excludes
  medications/referrals/follow-ups to keep the two passes from overlapping). Symptom
  extraction is normalized: the prompt instructs the LLM to extract only the canonical symptom
  name (`"cough"`, not `"productive cough with green sputum"`) as `extraction_text`, pushing
  qualifying detail not already captured by `body_part`/`severity`/`duration` into a `descriptor`
  attribute instead — this keeps the `Presentation` node's `text` consistent across consultations
  that describe the same symptom differently, rather than producing a different-looking node per
  phrasing. `descriptor` isn't a property `schema.json` defines on `Presentation` (only
  `name`/`severity`/`duration` are), same as the pre-existing `body_part` attribute — extra
  properties pass through unvalidated. If extraction quality needs tuning, this is where it
  happens.
- **`run_extraction(text, model_id, prompt, examples)`** — calls `lx.extract(...)` and normalizes
  the result into a list of `{text, attributes, position}` dicts. `position` holds character
  offsets (`char_interval.start_pos`/`end_pos`) into the original text, used later for source
  highlighting. Generalized over `prompt`/`examples` so it's reused for the symptom, diagnosis,
  medication, and investigation passes.
- **`build_entities_payload(symptoms, diagnoses, medications, investigations,
  encounter_datetime, clinical_notes, encounter_id)`** / **`_to_entity(...)`** — format symptoms,
  diagnoses, medications, and investigations into a JSON `{entities, relationships}` payload
  matching the Entity/Relationship contract used by the separate `cliniprompt-graph` project's
  Neo4j ingestion. Entity `type` values (`"Encounter"`, `"Presentation"`, `"Diagnosis"`,
  `"Medication"`, `"Procedure"`) are `schema.json` entity labels used directly as Neo4j node
  labels there, so they must stay capitalized exactly as in `schema.json`. Every payload has
  exactly one `Encounter` entity acting as the anchor node — its `id` is a `uuid4()` generated
  once per "Analyse" click and stored in `st.session_state.encounter_id` (passed in by the caller,
  not generated inside the function), its `encounter_date` property is captured as
  `datetime.now()` at the same moment (stored in `st.session_state.encounter_datetime`), and its
  `clinical_notes` property is the combined History/Examination/Diagnosis/Plan text
  (`st.session_state.original_text`), matching `schema.json`'s description of that field. Each
  Presentation/Diagnosis/Medication/Procedure entity gets a corresponding
  `PRESENTED_WITH`/`DIAGNOSED_WITH`/`PRESCRIBED`/`INCLUDED_PROCEDURE` relationship from the
  encounter. Medication is a deliberate schema simplification: `schema.json` models medications as
  two linked nodes (`Prescription` — the per-encounter dosage/route/duration/indication —
  connected via `FOR_MEDICATION` to a `Medication` drug concept with a unique `dm_d_id`), but this
  app flattens that into a single `Medication` entity per mention carrying the `Prescription`
  properties as attributes, linked directly from the encounter via `PRESCRIBED` — consistent with
  how `Diagnosis` is already flattened despite `schema.json` giving it a unique `snomed_code` too.
  The `Prescription` node and `FOR_MEDICATION` relationship are not produced by this app.
  Investigations extracted from the Plan field are similarly a simplification: `schema.json`'s
  `Procedure` entity has a `result` property and its `INCLUDED_PROCEDURE` relationship is described
  as "performed in this encounter," both implying a completed test, but anything pulled from the
  Plan field is an order, not a finished result — `result` is left unset and every extracted
  `Procedure` gets a hardcoded `status: "ordered"` attribute instead (set in code, not inferred by
  the LLM, since the Plan field itself is what establishes that status — see the extraction config
  bullet above). `status` isn't a `schema.json`-defined property on `Procedure`, same as
  `Presentation`'s `descriptor`/`body_part` — extra properties pass through unvalidated. There's
  still no Patient/Clinician/Facility wrapper — this app doesn't collect that metadata — and the
  app only populates the Encounter properties it actually collects (`encounter_date`,
  `clinical_notes`); other schema-defined Encounter properties (`encounter_type`,
  `chief_complaint`, `duration_minutes`, `outcome`) are omitted rather than guessed at.
- **`get_neo4j_driver()` / `push_encounter_to_neo4j(payload)` / `fetch_encounter_subgraph(encounter_id)`**
  — push the reviewed payload straight into Neo4j Aura and read it back for visualization.
  `get_neo4j_driver` is an `@st.cache_resource` singleton (one driver for the app's lifetime, per
  the Neo4j Python driver's guidance); returns `None` if `NEO4J_URI`/`NEO4J_USERNAME`/
  `NEO4J_PASSWORD` aren't set, which is how the UI decides whether to enable the "Push to Neo4j"
  button. `push_encounter_to_neo4j` runs `_push_encounter_tx` inside `session.execute_write` (one
  managed transaction, auto-retried): every entity is a plain `CREATE` (never `MERGE`) — each
  click of "Push to Neo4j" creates a fresh `Encounter` and its children, with no
  update-in-place/idempotent-repush behavior, matching a one-shot "review, then save" action.
  `ENTITY_ID_FIELDS` maps each label to the Neo4j-key property it's created with
  (`Encounter→encounter_id`, `Diagnosis→snomed_code`, `Medication→dm_d_id`,
  `Presentation→presentation_id`, `Procedure→procedure_id`) — this mirrors `_get_id_field` in
  `cliniprompt-graph/backend/graph.py`'s `save_encounter_to_graph` (a sibling project checked out
  locally at `~/Downloads/cliniprompt-graph`, the original consumer this payload shape was
  designed for) so data pushed from this app stays keyed the same way as data from that one, even
  though this app doesn't call that FastAPI service directly (it doesn't collect the
  Patient/Clinician info that service requires, and its `Relationship` model uses
  `from_entity`/`to_entity` where this app's payload uses `source`/`target`). Diagnosis is the one
  exception to "this app never extracts SNOMED/dm+d codes": the optional `search_snomed_bioportal`
  lookup (see below) lets a user pick a real `snomed_code` for a diagnosis before pushing, which
  lands in `properties` and is used as-is; without that, and always for Medication (nothing in this
  app ever populates `dm_d_id`), the entity gets a `f"temp-{uuid4()}"` placeholder id instead (same
  convention as the reference implementation).
  Presentation and Procedure have no natural key at all (this app never extracts SNOMED codes for
  investigations either, even though `schema.json`'s `Procedure` allows one) — both always get a
  fresh `uuid4()` rather than a `temp-` placeholder, since that placeholder specifically signals "a
  real-world code should exist here but wasn't extracted," which doesn't apply to either type.
  Cypher label/relationship-type
  strings are validated with `_safe_identifier` (`^[A-Za-z_][A-Za-z0-9_]*$`) before being
  f-string-interpolated into a query — defense-in-depth even though they only ever come from this
  app's own fixed vocabulary, never user input. `fetch_encounter_subgraph` re-queries the just-pushed
  Encounter and its immediate children for the visualization panel below (see next bullet) — it
  does not read the whole accumulated Aura graph, only the current session's encounter.
- **Graph visualization** — after a successful push, the result of `fetch_encounter_subgraph` is
  rendered with `neo4j_viz.neo4j.from_neo4j(result)` (Neo4j's own official Python graph
  visualization library) and embedded via `st.iframe(vg.render().data, height=500)` (not
  `st.components.v1.html`, which is deprecated), cached in `st.session_state.graph_viz_html` so it
  persists across reruns until the next "Analyse" click clears it. `neo4j-viz` was chosen over
  Neo4j Bloom (a separate
  standalone app, gated to Aura Business Critical/VDC tiers, not embeddable inline) and over NVL
  (React/JS, needs an npm/webpack build step — conflicts with this project's single-file,
  no-build-step design per the note above about not reintroducing a frontend split).
- **`get_source_context(symptom, original_text, padding=100)`** — reconstructs a highlighted
  snippet around an item's position for the "view source" (📍) toggle, entirely client-side
  from the stored offsets — there's no server-rendered HTML view like the old FastAPI
  `/visualize` endpoint had. Used by the symptoms, diagnoses, medications, and investigations
  panels.
- **`render_results_panel(...)`** — renders one results panel (list + 📍/✕ controls + "add new"
  form); parameterized by session-state keys and labels so it's reused for the Symptoms,
  Diagnoses, Medications, and Investigations tabs rather than duplicated. The Diagnoses tab passes
  `enable_snomed_lookup=True`; this is the only per-tab specialization the function has, everything
  else is identical across the four calls.
- **`search_snomed_bioportal(query, max_results=5)`** — looks up candidate SNOMED CT concept codes
  for a diagnosis's free text. SNOMED CT is licensed clinical terminology, so every legitimate
  source gates real content behind at least a free account — a live NHS England Terminology Server
  query, SNOMED International's own public browser, and a locally-hosted RF2 import (via `sct` or
  `hermes`) were all considered and rejected as too much friction/infra for this app's scope, in
  favour of a free BioPortal account + `BIOPORTAL_API_KEY`. Calls BioPortal's
  `https://data.bioontology.org/search` REST endpoint with `ontologies=SNOMEDCT`, and pulls the
  SNOMED CT concept id off the trailing segment of each result's `@id` URL (e.g.
  `.../SNOMEDCT/4556007` → `4556007`) rather than requesting BioPortal's separate `notation` field,
  since the URL is already present on every result by default. Returns up to `max_results`
  `{code, display}` dicts. Only wired into the Diagnoses panel — Symptoms/Medications/Investigations
  have no equivalent, matching the fact that `Diagnosis` is the only one of the four with a
  `snomed_code` id field in `ENTITY_ID_FIELDS` below. Inside `render_results_panel`, it's called
  on-demand from a "🔎 Find SNOMED code" button per diagnosis (not automatically on every
  "Analyse" click, to avoid a BioPortal call per diagnosis on every extraction) into a
  `st.session_state` candidates list; the resulting selectbox choice sets `snomed_code` and
  `snomed_display` directly on that item's `attributes` dict — mutated in place via
  `item.setdefault("attributes", {})` since `render_results_panel` iterates the same list object
  stored in `st.session_state`, so no extra plumbing is needed to get the choice to stick. Those
  attributes then flow through `_to_entity` into the entity's `properties` exactly like any other
  extracted attribute. `snomed_display` isn't a `schema.json`-defined property on `Diagnosis` (only
  `snomed_code` is), same as `Presentation`'s `descriptor` — an extra property that passes through
  unvalidated.
- **UI section** (bottom of the file) — a header row (`header_left`/`header_right` columns) with
  the "🏥 CliniPrompt GraphGen" title/caption on the left and a static, hardcoded mock patient
  banner (name, DOB/age, NHS number, sex, address — currently "Simpson, Homer" of 742 Evergreen
  Terrace, Springfield) right-aligned on the right, purely cosmetic to make the screen read like a
  clinical health record; it isn't wired to session state or `SAMPLE_CASES`, so it doesn't change
  when a sample case is loaded. The banner also renders a photo (`PATIENT_PHOTO_PATH`, resolved via
  `Path(__file__).parent` so it doesn't depend on the app's working directory, currently pointing
  at `homer.jpg` in the project root) as a 64px circular thumbnail immediately to its left, both
  wrapped in one flex row so the photo and text block right-align as a single unit; the image is
  read and base64-encoded fresh on every rerun (`base64.b64encode(PATIENT_PHOTO_PATH.read_bytes())`)
  and inlined as a `data:image/jpeg;base64,...` `<img src>` rather than passed to `st.image`, so it
  stays inside the same right-aligned flex container as the text instead of Streamlit laying it out
  as a separate element. Below that,
  a two-pane layout: a bordered `st.container` on the left holding the History/Examination/
  Diagnosis/Plan inputs (each `text_area` uses `height="content"` so it grows with what's typed
  instead of clipping at a fixed pixel height) with the "Analyse" button anchored at its bottom,
  directly under Plan — deliberately *not* a separate spacer column, so the button reads as the
  terminal action of the input card rather than an island between two panes. The right pane is a
  second bordered `st.container(height=700)` holding the tabbed results panel (Symptoms, Diagnoses,
  Medications, Investigations tabs, `height="stretch"` so the tab body fills the card); the fixed
  `height=700` gives it its own internal scrollbar once results are long, so reviewing a big
  extraction doesn't grow the whole page or push the input card out of view. The Analyse button has
  no `disabled` gating on input state — it's always clickable; the existing post-click validation
  (empty/too-short combined text) is what surfaces the error, not a greyed-out button. All app
  state (`symptoms`, `original_text`, `symptom_source_text`,
  `symptom_expanded_index`, `diagnoses`, `diagnosis_source_text`, `diagnosis_expanded_index`,
  `medications`, `medication_source_text`, `medication_expanded_index`, `investigations`,
  `investigation_source_text`, `investigation_expanded_index`, `error`, `encounter_datetime`,
  `encounter_id`, `neo4j_push_status`, `graph_viz_html`, `collapse_sidebar`,
  `sidebar_expand_checked`) lives in `st.session_state`, which is scoped per browser session.
  `original_text` (the combined History/Examination/Diagnosis/Plan text) is kept only for the
  Encounter's `clinical_notes` property — `symptom_source_text` (History only),
  `diagnosis_source_text` (Diagnosis only), `medication_source_text` (Plan only), and
  `investigation_source_text` (also Plan only — duplicated from the same field rather than shared
  with `medication_source_text`, keeping the one-key-per-panel convention consistent even though
  the underlying text is identical) are what each results panel's "view source" (📍) highlighting
  is actually reconstructed from, so offsets line up with the field each extraction pass ran
  against. This was a deliberate fix for a bug in the
  old FastAPI backend, which stored the last extraction result as attributes on the global `app`
  object — safe for one user, broken for concurrent ones. Don't reintroduce module-level/global
  mutable state for request data.
- **`SAMPLE_CASES`** / sidebar loader — a dict of sample case name → `{history, examination,
  diagnosis, plan}` text. All four cases (Sleep Apnoea, Gastritis, Exertional Angina, Gout) are
  written to read as presentations from the same "Homer Simpson" mock patient the header banner
  represents, matching his age (49) and lifestyle (diet, alcohol, obesity) rather than being
  demographically generic. Unlike the rest of the file's string constants, these four are kept as
  verbatim clinician shorthand — multi-line triple-quoted strings preserving the original line
  breaks and abbreviations (`1/52`, `ETOH`, `NAD`, `U+E`, `Imp`, bullet-style plan lines, etc.)
  exactly as drafted, rather than normalized into full prose sentences — this was a deliberate
  choice (the user asked to keep their own text/shorthand/formatting rather than have it rewritten)
  and should be preserved if these cases are edited again; don't "clean up" the abbreviations back
  into prose. One consequence: the "Exertional Angina" case has no explicit "Impression -" line in
  the source notes, so its `diagnosis` value reuses the case's own heading text ("Exertional
  Angina") rather than inventing a diagnostic sentence. The sidebar (`st.sidebar`, rendered right
  after the API-key check) has a selectbox over `SAMPLE_CASES` and a "Load Sample Case" button that
  writes the chosen case's fields directly into
  `st.session_state.history`/`.examination`/`.diagnosis`/`.plan` (the same
  keys the four `text_area` widgets use), sets `st.session_state.collapse_sidebar = True`, and
  calls `st.rerun()`. This relies on the sidebar block executing *before* the `text_area` widgets
  are instantiated later in the script — Streamlit requires a widget's session-state value to be
  set before that widget is created on the same run, so don't move this block below the
  `left, center, right` columns or the load will silently no-op on the next widget instantiation.
  `st.set_page_config(..., initial_sidebar_state="expanded")` keeps the sidebar (and the Sample
  Cases section in it) open on first load. Right after the sidebar block, a check on
  `st.session_state.collapse_sidebar` fires a one-shot `st.components.v1.html` snippet that finds
  and clicks the sidebar's own collapse button (`[data-testid="stSidebarCollapseButton"] button`)
  in the parent document, then immediately resets the flag to `False` — this is what auto-collapses
  the sidebar after "Load Sample Case" so the user doesn't have to click the collapse arrow
  themselves. It has to be a real simulated click on Streamlit's own control (rather than e.g.
  reissuing `initial_sidebar_state` on rerun) because Streamlit persists the sidebar's
  expanded/collapsed state to the browser's `localStorage` (key `stSidebarCollapsed-`) once the
  user (or a simulated click) toggles it, and that persisted value takes precedence over
  `initial_sidebar_state` on every subsequent load — not just later reruns in the same session, but
  every future session in that browser too. That means the auto-collapse above, left unchecked,
  would leave every later fresh page load starting collapsed even though
  `initial_sidebar_state="expanded"` says otherwise. A second one-shot-per-session guard
  (`st.session_state.sidebar_expand_checked`, checked immediately after the collapse block) corrects
  this: on the first script run of a session it simulates a click on the sidebar's expand control
  (`[data-testid="stExpandSidebarButton"]`, the small `>>` control shown when the sidebar is
  collapsed — a different element from the collapse button above, only present in the DOM when
  collapsed, so the click is a no-op if the sidebar is already open) and flips the flag so it won't
  fire again later in the same session — otherwise it would re-expand a sidebar the user (or the
  sample-case loader) deliberately collapsed mid-session.

Symptoms, diagnoses, medications, and investigations can each be added manually (via a form) or
removed, independent of extraction — the lists in
`st.session_state.symptoms`/`.diagnoses`/`.medications`/`.investigations` are the single source of
truth once populated, not re-derived from the LLM result after edits. Manually-added investigations
still get `status: "ordered"` applied in `build_entities_payload` (it's set on every `Procedure`
entity regardless of origin), not just ones that came from extraction.

The default `model_id` is `"gemini-3.5-flash-lite"` (`DEFAULT_MODEL_ID`), used directly with no UI
control to edit it — the model name isn't something an end user of this app needs to see or
change. This was never fully verified against the active API key/provider, so if extraction calls
start failing, check this constant first.

`REQUEST_GUIDE.md` documents Gemini free-tier rate limits (20 RPM / 300 QPD) and how
`extraction_passes`, `max_workers`, and `max_char_buffer` affect request volume — relevant if
`run_extraction` is ever changed to process multiple documents or use more than one pass. Each
"Analyse" click now makes four `lx.extract` calls (symptoms, diagnoses, medications,
investigations) rather than three — worth keeping in mind against the 20 RPM ceiling if another
extraction pass is added.

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
