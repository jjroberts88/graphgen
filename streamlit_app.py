#!/usr/bin/env python3
"""Streamlit app for clinical consultation symptom extraction."""

import base64
import json
import os
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import langextract as lx
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j_viz.neo4j import from_neo4j

# Look for a .env at the project root first, then fall back to backend/.env
# so the app works without extra setup for anyone who already had the
# FastAPI backend configured.
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env", override=False)

API_KEY = os.getenv("LANGEXTRACT_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

BIOPORTAL_API_KEY = os.getenv("BIOPORTAL_API_KEY")

DEFAULT_MODEL_ID = "gemini-3.5-flash-lite"

PATIENT_PHOTO_PATH = Path(__file__).parent / "homer.jpg"

EXTRACTION_PROMPT = """Extract all medical symptoms mentioned in this patient history.

For each symptom, extract only its core/canonical name, e.g. "cough" (not "productive
cough with green sputum"), "headache" (not "severe left-sided throbbing headache"). Do not
fold descriptive detail, qualifiers, or associated features into the symptom name itself,
and do not combine multiple distinct symptoms into one extraction.

For each symptom, identify:
- The core symptom name (canonical form, not the full descriptive phrase)
- The body part or area affected (if mentioned)
- The severity (if mentioned)
- The duration (if mentioned)
- The descriptor: any other qualifying detail from the text not already captured above,
  e.g. colour, character, quality, or associated features ("productive, green sputum",
  "throbbing", "worse on movement")

List symptoms in the order they appear in the text."""

EXTRACTION_EXAMPLES = [
    lx.data.ExampleData(
        text="""Patient reports persistent headache that started 2 days ago, throbbing
        and worse on movement. She also complains of mild fever and a productive cough
        with green sputum. Additionally, the patient has noticed a sore throat.""",
        extractions=[
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="headache",
                attributes={
                    "body_part": "head",
                    "severity": "persistent",
                    "duration": "started 2 days ago",
                    "descriptor": "throbbing, worse on movement",
                },
            ),
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="fever",
                attributes={
                    "body_part": "systemic",
                    "severity": "mild",
                    "duration": None,
                    "descriptor": None,
                },
            ),
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="cough",
                attributes={
                    "body_part": "chest",
                    "severity": None,
                    "duration": None,
                    "descriptor": "productive, green sputum",
                },
            ),
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="sore throat",
                attributes={
                    "body_part": "throat",
                    "severity": None,
                    "duration": None,
                    "descriptor": None,
                },
            ),
        ],
    )
]

# Mirrors the Diagnosis entity in schema.json (status/certainty enums). Runs
# against the Diagnosis field only, not the combined consultation text — that
# field is where clinicians enter diagnosis data, so it's the right scope for
# this extraction (unlike symptoms, which can appear anywhere in the note).
DIAGNOSIS_EXTRACTION_PROMPT = """Extract all diagnoses or clinical impressions mentioned in this text.
For each diagnosis, identify:
- The exact diagnosis name as mentioned in the text
- The status: suspected, confirmed, resolved, or chronic_ongoing (if mentioned or implied)
- The certainty: definite, probable, or possible (if mentioned or implied)

Use exact text from the document. Do not paraphrase or combine diagnoses.
List diagnoses in the order they appear in the text."""

DIAGNOSIS_EXTRACTION_EXAMPLES = [
    lx.data.ExampleData(
        text="""Likely community-acquired pneumonia, probable diagnosis pending chest X-ray.
        Chronic hypertension, well controlled on current medication. Query early
        appendicitis - suspected, referred for surgical review.""",
        extractions=[
            lx.data.Extraction(
                extraction_class="diagnosis",
                extraction_text="community-acquired pneumonia",
                attributes={
                    "status": "suspected",
                    "certainty": "probable",
                },
            ),
            lx.data.Extraction(
                extraction_class="diagnosis",
                extraction_text="chronic hypertension",
                attributes={
                    "status": "chronic_ongoing",
                    "certainty": "definite",
                },
            ),
            lx.data.Extraction(
                extraction_class="diagnosis",
                extraction_text="appendicitis",
                attributes={
                    "status": "suspected",
                    "certainty": "possible",
                },
            ),
        ],
    )
]



# Mirrors the flat-per-mention shape used for diagnoses above, rather than the
# two-node Prescription->Medication split defined in schema.json (Prescription
# holds dosage/route/duration/indication, Medication holds the drug concept
# with a unique dm_d_id). Flattening keeps this extraction on the same
# 1-extraction-to-1-entity pattern as symptoms/diagnoses; dosage/route/
# duration/indication become attributes on a single Medication entity instead
# of a separate linked Prescription entity. Runs against the Plan field only.
MEDICATION_EXTRACTION_PROMPT = """Extract all medications prescribed or recommended in this treatment plan.

For each medication, extract only its core/canonical drug name, e.g. "amoxicillin" (not
"empirical oral antibiotics (amoxicillin)"). Do not combine multiple distinct medications
into one extraction.

For each medication, identify the following, using only what is explicitly stated in the text
for that medication. Do not infer, guess, or carry over a value from context, and never copy one
field's value into another field:
- The dosage: the amount and/or frequency, e.g. "500mg three times daily". Leave blank if no
  dosage is stated.
- The route: oral, topical, inhaled, injection, or other. Leave blank unless an explicit word
  in the text states the route (e.g. "topically", "inhaled", "IV", "cream applied to").
- The duration: how long the medication should be taken for, e.g. "7 days". Leave blank if no
  duration is stated. Duration is how long the course runs, not how often it's taken.
- The indication: the reason for prescribing, stated in the text, e.g. "for pain". Leave blank
  if no reason is given — do not guess a clinical rationale.

When a field is not explicitly stated for a given medication, leave it blank. A blank field is
correct and expected more often than not — do not fill it with a plausible-sounding guess.

Use exact text from the document for the drug name. Do not paraphrase or combine
medications. List medications in the order they appear in the text."""

MEDICATION_EXTRACTION_EXAMPLES = [
    lx.data.ExampleData(
        text="""Start amoxicillin 500mg three times daily for 7 days for suspected chest
        infection. Continue paracetamol 1g four times daily as required for pain. Apply
        hydrocortisone cream topically twice daily to the affected area. Continue metformin
        as before.""",
        extractions=[
            lx.data.Extraction(
                extraction_class="medication",
                extraction_text="amoxicillin",
                attributes={
                    "dosage": "500mg three times daily",
                    "route": "oral",
                    "duration": "7 days",
                    "indication": "suspected chest infection",
                },
            ),
            lx.data.Extraction(
                extraction_class="medication",
                extraction_text="paracetamol",
                attributes={
                    "dosage": "1g four times daily as required",
                    "route": "oral",
                    "duration": None,
                    "indication": "pain",
                },
            ),
            lx.data.Extraction(
                extraction_class="medication",
                extraction_text="hydrocortisone",
                attributes={
                    "dosage": "twice daily",
                    "route": "topical",
                    "duration": None,
                    "indication": None,
                },
            ),
            lx.data.Extraction(
                extraction_class="medication",
                extraction_text="metformin",
                attributes={
                    "dosage": None,
                    "route": None,
                    "duration": None,
                    "indication": None,
                },
            ),
        ],
    )
]

PROCEDURE_EXTRACTION_PROMPT = """Extract all investigations, diagnostic tests, or procedures
ordered or arranged in this treatment plan (e.g. blood tests, imaging, ECGs). Do not extract
medications, prescriptions, referrals to a specialty/service, or follow-up appointments.

For each investigation, extract only its core/canonical name, e.g. "chest X-ray" (not "arrange
chest X-ray"), "full blood count" (not "bloods including FBC and CRP" as a single item — split
into separate investigations). Use exact text from the document. Do not combine multiple
distinct investigations into one extraction. List investigations in the order they appear in
the text."""

PROCEDURE_EXTRACTION_EXAMPLES = [
    lx.data.ExampleData(
        text="""Start empirical oral antibiotics (amoxicillin), arrange chest X-ray and bloods
        including CRP and blood cultures. Advise safety-net for worsening breathlessness.
        Review in 48 hours or sooner if deteriorating.""",
        extractions=[
            lx.data.Extraction(
                extraction_class="investigation",
                extraction_text="chest X-ray",
                attributes={},
            ),
            lx.data.Extraction(
                extraction_class="investigation",
                extraction_text="CRP",
                attributes={},
            ),
            lx.data.Extraction(
                extraction_class="investigation",
                extraction_text="blood cultures",
                attributes={},
            ),
        ],
    )
]


SAMPLE_CASES = {
    "Snoring & Daytime Sleepiness": {
        "history": """Wife Marge reports increased snoring last 6/12. Episodes of pauses in breathing during sleep. Wakes up gasping. Sleep unrefreshing and feeling excessive sleepiness during day. Impacting work as nuclear safety officer - often falling asleep at work.
Non smoker. Alcohol 6 units 3-4x a week. Obese.
Driving.""",
        "examination": """BP 151/81
Pulse 78 regular
Chest clear.
Throat examination NAD.
Neck circumference 49cm
Epworth score 16
Weight 108kg
BMI 35""",
        "diagnosis": "1) Obstructive sleep apnoea 2) Obesity 3) Hypertension",
        "plan": """Bloods - FBC, U+E, LFTs, Lipid profile, HbA1C, TFT
Ambulatory BP monitor
ECG
Weight management referral
Advised to reduce ETOH
Referral to sleep clinic for OSA
Patient information leaflet provided
Review with results of above""",
    },
    "Epigastric Pain": {
        "history": """Presents with 1/52 epigastric pain and retrosternal acid sensation/burning. Associated with excessive belching. No dysphagia. No black or bloody stools. No vomiting. No weight loss. Pain is not exertional.
Symptoms started after entering 'chilli eating' contest followed by ++beer
No NSAID use""",
        "examination": """BP 147/71
Pulse 72
Temp 36.5c
Chest clear
Abdo soft, nil masses, mild epigastric tenderness""",
        "diagnosis": "Gastritis",
        "plan": """Omeprazole 20mg PO OD for 4/52
H Pylori stool test
Routine bloods to check FBC, CRP, U+E, LFT, Lipase
Advised to avoid spicy food/ETOH/NSAIDs
Review with results
Seek review if worsening symptoms""",
    },
    "Exertional Chest Tightness": {
        "history": """Presents with 4/12 history of central chest tightness on exertion. No radiation to arms/neck. Some associated SOB. No presyncope/syncope.
Symptoms occurring on inclines after 50m.
No rest pain.
Prev successful CABG aged 36y
Not used GTN.
Non smoker""",
        "examination": """BP 146/71
P 83 regular
Heart sounds normal
Chest clear on auscultation
No pedal oedema.""",
        "diagnosis": "Exertional Angina",
        "plan": """ECG
Bloods - check FBC, U+E, HbA1C, Lipid profile
Referral to cardiology
Prescribed GTN spray and advised on use
Seek urgent medical review if increasing/severe pain""",
    },
    "Painful Swollen Toe": {
        "history": """Presents with 2/7 history of pain, swelling and erythema in right Hallux MTPJ. No trauma. No prev occurrence. Started after summer BBQ with beer + ribs.
No fever.""",
        "examination": """BP 139/61
P 65
Temp 36.1c

Right Hallux MTPJ tender, erythema. Able to flex. No tracking cellulitis. Foot pulses normal. Capillary refil <2s""",
        "diagnosis": "Gout",
        "plan": """colchicine
Patient advice leaflet on gout and diet modification
Advised for blood test in 6 weeks to check uric acid levels and consider allopurinol at this point.""",
    },
}


def run_extraction(text: str, model_id: str, prompt: str, examples: list) -> list[dict]:
    result = lx.extract(
        text_or_documents=text,
        prompt_description=prompt,
        examples=examples,
        model_id=model_id,
        extraction_passes=1,
        max_workers=1,
    )

    items = []
    for extraction in result.extractions:
        items.append(
            {
                "text": extraction.extraction_text,
                "attributes": extraction.attributes or {},
                "position": {
                    "start": extraction.char_interval.start_pos,
                    "end": extraction.char_interval.end_pos,
                }
                if extraction.char_interval
                else None,
            }
        )
    return items


# Matches the Entity/Relationship contract used by cliniprompt-graph's Neo4j
# ingestion (backend/models.py Entity + Relationship, consumed by graph.py's
# save_encounter_to_graph). `type` values ("Presentation", "Diagnosis",
# "Medication") are schema.json entity labels, used directly as Neo4j node
# labels there — so they must stay capitalized exactly as in schema.json.
# Medication is flattened onto the Encounter-[PRESCRIBED]->Medication edge
# rather than schema.json's Encounter->Prescription->Medication chain (see
# MEDICATION_EXTRACTION_PROMPT above) — the Prescription node and its
# FOR_MEDICATION relationship are not produced by this app.
# Still no Patient/Clinician/Facility wrapper (GraphGen doesn't collect that
# metadata); build_entities_payload() below adds the Encounter anchor node
# and the Encounter-[PRESENTED_WITH/DIAGNOSED_WITH/PRESCRIBED]->entity
# relationships.
def _to_entity(item: dict, idx: int, id_prefix: str, entity_type: str) -> dict:
    position = item.get("position") or {}
    return {
        "id": f"{id_prefix}-{idx}",
        "text": item.get("text", ""),
        "type": entity_type,
        "start": position.get("start", 0),
        "end": position.get("end", 0),
        "properties": item.get("attributes") or {},
    }


def build_entities_payload(
    symptoms: list[dict],
    diagnoses: list[dict],
    medications: list[dict],
    investigations: list[dict],
    encounter_datetime: datetime,
    clinical_notes: str,
    encounter_id: str,
) -> dict:
    encounter = {
        "id": encounter_id,
        "text": clinical_notes,
        "type": "Encounter",
        "start": 0,
        "end": len(clinical_notes),
        "properties": {
            "encounter_date": encounter_datetime.isoformat(),
            "clinical_notes": clinical_notes,
        },
    }
    presentations = [_to_entity(item, idx, "presentation", "Presentation") for idx, item in enumerate(symptoms, 1)]
    diagnosis_entities = [_to_entity(item, idx, "diagnosis", "Diagnosis") for idx, item in enumerate(diagnoses, 1)]
    medication_entities = [
        _to_entity(item, idx, "medication", "Medication") for idx, item in enumerate(medications, 1)
    ]
    procedure_entities = [
        _to_entity(item, idx, "procedure", "Procedure") for idx, item in enumerate(investigations, 1)
    ]
    for entity in procedure_entities:
        entity["properties"].setdefault("status", "ordered")

    relationships = (
        [{"type": "PRESENTED_WITH", "source": encounter_id, "target": entity["id"]} for entity in presentations]
        + [{"type": "DIAGNOSED_WITH", "source": encounter_id, "target": entity["id"]} for entity in diagnosis_entities]
        + [{"type": "PRESCRIBED", "source": encounter_id, "target": entity["id"]} for entity in medication_entities]
        + [{"type": "INCLUDED_PROCEDURE", "source": encounter_id, "target": entity["id"]} for entity in procedure_entities]
    )

    return {
        "entities": [encounter] + presentations + diagnosis_entities + medication_entities + procedure_entities,
        "relationships": relationships,
    }


_CYPHER_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(value: str) -> str:
    if not _CYPHER_IDENTIFIER_RE.match(value):
        raise ValueError(f"Unsafe Cypher identifier: {value!r}")
    return value


# Per-type natural id field used as each label's Neo4j key, mirroring
# cliniprompt-graph/backend/graph.py's _get_id_field (the separate FastAPI project this
# payload's entity/relationship shape was designed to feed) so data from both apps stays
# keyed consistently in the same graph.
ENTITY_ID_FIELDS = {
    "Encounter": "encounter_id",
    "Presentation": "presentation_id",
    "Diagnosis": "snomed_code",
    "Medication": "dm_d_id",
    "Procedure": "procedure_id",
}


@st.cache_resource
def get_neo4j_driver():
    if not (NEO4J_URI and NEO4J_USERNAME and NEO4J_PASSWORD):
        return None
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    driver.verify_connectivity()
    return driver


def _push_encounter_tx(tx, payload: dict) -> tuple[int, int]:
    entity_map = {}  # payload entity id -> (label, persisted id)
    nodes_created = 0

    for entity in payload["entities"]:
        entity_type = _safe_identifier(entity["type"])
        id_field = ENTITY_ID_FIELDS[entity_type]

        if entity_type == "Encounter":
            persisted_id = entity["id"]
        elif entity_type in ("Presentation", "Procedure"):
            # No natural key for symptoms/investigations (unlike Diagnosis/Medication's
            # SNOMED/dm+d codes) — each mention is its own node.
            persisted_id = str(uuid4())
        else:
            persisted_id = entity["properties"].get(id_field) or f"temp-{uuid4()}"

        properties = {id_field: persisted_id, "created_at": datetime.now(), **entity["properties"]}
        if entity_type != "Encounter":
            properties.setdefault("name", entity["text"])

        prop_str = ", ".join(f"{k}: ${k}" for k in properties)
        tx.run(f"CREATE (n:{entity_type} {{{prop_str}}})", **properties)
        entity_map[entity["id"]] = (entity_type, persisted_id)
        nodes_created += 1

    rels_created = 0
    for rel in payload["relationships"]:
        from_type, from_id = entity_map[rel["source"]]
        to_type, to_id = entity_map[rel["target"]]
        from_field, to_field = ENTITY_ID_FIELDS[from_type], ENTITY_ID_FIELDS[to_type]
        rel_type = _safe_identifier(rel["type"])
        tx.run(
            f"MATCH (from:{from_type} {{{from_field}: $from_id}}), (to:{to_type} {{{to_field}: $to_id}}) "
            f"CREATE (from)-[:{rel_type}]->(to)",
            from_id=from_id,
            to_id=to_id,
        )
        rels_created += 1

    return nodes_created, rels_created


def push_encounter_to_neo4j(payload: dict) -> tuple[int, int]:
    driver = get_neo4j_driver()
    if driver is None:
        raise RuntimeError("Neo4j is not configured (set NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD in .env)")
    with driver.session(database=NEO4J_DATABASE) as session:
        return session.execute_write(_push_encounter_tx, payload)


def fetch_encounter_subgraph(encounter_id: str):
    driver = get_neo4j_driver()
    return driver.execute_query(
        "MATCH (e:Encounter {encounter_id: $id})-[r]->(child) RETURN e, r, child",
        id=encounter_id,
        database_=NEO4J_DATABASE,
    )


def search_snomed_bioportal(query: str, max_results: int = 5) -> list[dict]:
    """Look up candidate SNOMED CT concepts for free-text diagnosis via BioPortal."""
    response = requests.get(
        "https://data.bioontology.org/search",
        params={"q": query, "ontologies": "SNOMEDCT", "pagesize": max_results, "apikey": BIOPORTAL_API_KEY},
        timeout=10,
    )
    response.raise_for_status()
    candidates = []
    for result in response.json().get("collection", [])[:max_results]:
        code = result.get("@id", "").rsplit("/", 1)[-1]
        if code:
            candidates.append({"code": code, "display": result.get("prefLabel", "")})
    return candidates


def get_source_context(symptom: dict, original_text: str, padding: int = 100):
    position = symptom.get("position")
    if not position or not original_text:
        return None

    start, end = position["start"], position["end"]
    context_start = max(0, start - padding)
    context_end = min(len(original_text), end + padding)

    return {
        "before": original_text[context_start:start],
        "highlighted": original_text[start:end],
        "after": original_text[end:context_end],
    }


def render_results_panel(state_key, source_text_key, expanded_key, panel_title, item_name, enable_snomed_lookup=False):
    items = st.session_state[state_key]
    if not items:
        st.info(f'Click "Analyse" to extract {item_name}s from the clinical data')
        return

    st.subheader(f"{panel_title} ({len(items)})")

    for idx, item in enumerate(items):
        text_col, source_col, delete_col = st.columns([6, 1, 1])
        text_col.markdown(f"**{item['text']}**")

        context = get_source_context(item, st.session_state[source_text_key])
        if context and source_col.button("📍", key=f"{state_key}_source_{idx}"):
            st.session_state[expanded_key] = None if st.session_state[expanded_key] == idx else idx

        if delete_col.button("✕", key=f"{state_key}_delete_{idx}"):
            st.session_state[state_key].pop(idx)
            st.rerun()

        attributes = item.setdefault("attributes", {})
        attr_bits = [f"**{k.replace('_', ' ').title()}:** {v}" for k, v in attributes.items() if v]
        if attr_bits:
            st.caption(" · ".join(attr_bits))

        if enable_snomed_lookup and BIOPORTAL_API_KEY:
            candidates_key = f"{state_key}_snomed_candidates_{idx}"
            if st.button("🔎 Find SNOMED code", key=f"{state_key}_snomed_search_{idx}"):
                try:
                    st.session_state[candidates_key] = search_snomed_bioportal(item["text"])
                except requests.RequestException as e:
                    st.session_state[candidates_key] = []
                    st.error(f"SNOMED lookup failed: {e}")

            candidates = st.session_state.get(candidates_key)
            if candidates:
                options = ["Select a match..."] + [f"{c['code']} — {c['display']}" for c in candidates]
                choice = st.selectbox(
                    "SNOMED CT match", options, key=f"{state_key}_snomed_choice_{idx}", label_visibility="collapsed"
                )
                if choice != "Select a match...":
                    chosen = candidates[options.index(choice) - 1]
                    attributes["snomed_code"] = chosen["code"]
                    attributes["snomed_display"] = chosen["display"]
            elif candidates == []:
                st.caption("No SNOMED CT matches found.")

        if context and st.session_state[expanded_key] == idx:
            st.markdown(
                f"Source: _{context['before']}_ "
                f":orange[**{context['highlighted']}**] "
                f"_{context['after']}_"
            )

        st.divider()

    with st.form(f"add_{state_key}_form", clear_on_submit=True):
        add_col, submit_col = st.columns([5, 1])
        new_text = add_col.text_input(
            f"Add new {item_name}", placeholder=f"Add new {item_name}...", label_visibility="collapsed"
        )
        submitted = submit_col.form_submit_button("Add")
        if submitted and new_text.strip():
            st.session_state[state_key].append({"text": new_text.strip(), "attributes": {}, "position": None})
            st.rerun()


st.set_page_config(
    page_title="Clinical Consultation Analyzer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "symptoms" not in st.session_state:
    st.session_state.symptoms = []
if "original_text" not in st.session_state:
    st.session_state.original_text = ""
if "symptom_source_text" not in st.session_state:
    st.session_state.symptom_source_text = ""
if "symptom_expanded_index" not in st.session_state:
    st.session_state.symptom_expanded_index = None
if "diagnoses" not in st.session_state:
    st.session_state.diagnoses = []
if "diagnosis_source_text" not in st.session_state:
    st.session_state.diagnosis_source_text = ""
if "diagnosis_expanded_index" not in st.session_state:
    st.session_state.diagnosis_expanded_index = None
if "medications" not in st.session_state:
    st.session_state.medications = []
if "medication_source_text" not in st.session_state:
    st.session_state.medication_source_text = ""
if "medication_expanded_index" not in st.session_state:
    st.session_state.medication_expanded_index = None
if "investigations" not in st.session_state:
    st.session_state.investigations = []
if "investigation_source_text" not in st.session_state:
    st.session_state.investigation_source_text = ""
if "investigation_expanded_index" not in st.session_state:
    st.session_state.investigation_expanded_index = None
if "error" not in st.session_state:
    st.session_state.error = ""
if "encounter_datetime" not in st.session_state:
    st.session_state.encounter_datetime = None
if "encounter_id" not in st.session_state:
    st.session_state.encounter_id = None
if "neo4j_push_status" not in st.session_state:
    st.session_state.neo4j_push_status = ""
if "graph_viz_html" not in st.session_state:
    st.session_state.graph_viz_html = None
if "collapse_sidebar" not in st.session_state:
    st.session_state.collapse_sidebar = False
if "sidebar_expand_checked" not in st.session_state:
    st.session_state.sidebar_expand_checked = False

def reset_case_state(clear_fields: bool = False) -> None:
    """Clear all extraction results and encounter state for the current case.

    Used both by "New Case" (which also blanks the input fields) and by
    "Load Sample Case" (which leaves clear_fields False since it immediately
    overwrites the fields with the new case's text) - switching cases
    shouldn't leave a previous case's stale results/encounter_id/graph
    lingering in the results panel.
    """
    st.session_state.symptoms = []
    st.session_state.diagnoses = []
    st.session_state.medications = []
    st.session_state.investigations = []

    # Dynamic per-item SNOMED lookup keys (see render_results_panel) aren't
    # covered by the state_key resets above since they're keyed by item index
    # - without this, a new case's item at the same index could pick up a
    # stale SNOMED candidate list/choice from the previous case.
    for key in list(st.session_state.keys()):
        if any(
            key.startswith(f"{state_key}_snomed_")
            for state_key in ("symptoms", "diagnoses", "medications", "investigations")
        ):
            del st.session_state[key]

    st.session_state.symptom_source_text = ""
    st.session_state.diagnosis_source_text = ""
    st.session_state.medication_source_text = ""
    st.session_state.investigation_source_text = ""
    st.session_state.symptom_expanded_index = None
    st.session_state.diagnosis_expanded_index = None
    st.session_state.medication_expanded_index = None
    st.session_state.investigation_expanded_index = None
    st.session_state.original_text = ""
    st.session_state.encounter_datetime = None
    st.session_state.encounter_id = None
    st.session_state.neo4j_push_status = ""
    st.session_state.graph_viz_html = None
    st.session_state.error = ""

    if clear_fields:
        st.session_state.history = ""
        st.session_state.examination = ""
        st.session_state.diagnosis = ""
        st.session_state.plan = ""


header_left, header_right = st.columns([3, 1])

with header_left:
    st.title("🧬 CliniPrompt GraphGen")
    st.caption("Create a clinical knowledge graph (CKG) from clinical notes")

with header_right:
    photo_b64 = base64.b64encode(PATIENT_PHOTO_PATH.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: flex-end;
                    gap: 0.75rem; padding-top: 1.5rem;">
            <div style="text-align: right; line-height: 1.6;">
                <div><strong>Simpson, Homer</strong></div>
                <div>DOB: 12-Feb-1977 (49y)</div>
                <div>NHS No: 485 773 2091</div>
                <div>Sex: Male</div>
                <div>Address: 742 Evergreen Terrace, Springfield</div>
            </div>
            <img src="data:image/jpeg;base64,{photo_b64}"
                 style="width: 64px; height: 64px; object-fit: cover; border-radius: 50%;" />
        </div>
        """,
        unsafe_allow_html=True,
    )

if not API_KEY:
    st.error(
        "LANGEXTRACT_API_KEY environment variable not set. "
        "Add it to a .env file in the project root (or backend/.env)."
    )
    st.stop()

if st.session_state.error:
    st.error(st.session_state.error)

with st.sidebar:
    st.subheader("Sample Cases")
    st.caption("Load prepopulated case details into the entry fields.")
    selected_case = st.selectbox("Choose a sample case", options=list(SAMPLE_CASES.keys()))
    if st.button("Load Sample Case", use_container_width=True):
        case = SAMPLE_CASES[selected_case]
        reset_case_state()
        st.session_state.history = case["history"]
        st.session_state.examination = case["examination"]
        st.session_state.diagnosis = case["diagnosis"]
        st.session_state.plan = case["plan"]
        st.session_state.collapse_sidebar = True
        st.rerun()

if st.session_state.collapse_sidebar:
    st.session_state.collapse_sidebar = False
    components.html(
        """
        <script>
            const btn = window.parent.document.querySelector(
                '[data-testid="stSidebarCollapseButton"] button'
            );
            if (btn) { btn.click(); }
        </script>
        """,
        height=0,
        width=0,
    )

# Streamlit persists the sidebar's collapsed/expanded state to the browser's
# localStorage once toggled (including by the auto-collapse above), and that
# persisted value takes precedence over initial_sidebar_state="expanded" on
# every future load in that browser - so a stale "collapsed" from a previous
# session's "Load Sample Case" would otherwise start every new session
# collapsed too. Once per session, correct that by clicking the sidebar's
# own expand control if it's present (i.e. only if currently collapsed).
if not st.session_state.sidebar_expand_checked:
    st.session_state.sidebar_expand_checked = True
    components.html(
        """
        <script>
            const btn = window.parent.document.querySelector(
                '[data-testid="stExpandSidebarButton"]'
            );
            if (btn) { btn.click(); }
        </script>
        """,
        height=0,
        width=0,
    )

left, right = st.columns([1, 1.2], gap="large")

with left:
    if st.button("🆕 New Case", use_container_width=True):
        reset_case_state(clear_fields=True)
        st.rerun()

    with st.container(border=True, height="content"):
        st.markdown("**History**")
        history = st.text_area("History", key="history", placeholder="Enter patient history...", height="content", label_visibility="collapsed")

        st.markdown("**Examination**")
        examination = st.text_area("Examination", key="examination", placeholder="Enter examination findings...", height="content", label_visibility="collapsed")

        st.markdown("**Diagnosis**")
        diagnosis = st.text_area("Diagnosis", key="diagnosis", placeholder="Enter diagnosis...", height="content", label_visibility="collapsed")

        st.markdown("**Plan**")
        plan = st.text_area("Plan", key="plan", placeholder="Enter treatment plan...", height="content", label_visibility="collapsed")

        st.divider()
        model_id = DEFAULT_MODEL_ID
        analyse_clicked = st.button("Analyse", use_container_width=True, type="primary")

with right:
    results_pane = st.container(border=True, height=700)

with results_pane:
    if analyse_clicked:
        all_text = f"History: {history}\n\nExamination: {examination}\n\nDiagnosis: {diagnosis}\n\nPlan: {plan}"

        if not all_text.strip() or len(all_text) < 50:
            st.session_state.error = "Please fill in the clinical data fields"
        else:
            st.session_state.error = ""
            with st.spinner("Analysing..."):
                try:
                    st.session_state.encounter_datetime = datetime.now()
                    st.session_state.encounter_id = str(uuid4())
                    st.session_state.original_text = all_text
                    st.session_state.neo4j_push_status = ""
                    st.session_state.graph_viz_html = None

                    if history.strip():
                        st.session_state.symptoms = run_extraction(
                            history, model_id, EXTRACTION_PROMPT, EXTRACTION_EXAMPLES
                        )
                        st.session_state.symptom_source_text = history
                    else:
                        st.session_state.symptoms = []
                        st.session_state.symptom_source_text = ""
                    st.session_state.symptom_expanded_index = None

                    if diagnosis.strip():
                        st.session_state.diagnoses = run_extraction(
                            diagnosis, model_id, DIAGNOSIS_EXTRACTION_PROMPT, DIAGNOSIS_EXTRACTION_EXAMPLES
                        )
                        st.session_state.diagnosis_source_text = diagnosis
                    else:
                        st.session_state.diagnoses = []
                        st.session_state.diagnosis_source_text = ""
                    st.session_state.diagnosis_expanded_index = None

                    if plan.strip():
                        st.session_state.medications = run_extraction(
                            plan, model_id, MEDICATION_EXTRACTION_PROMPT, MEDICATION_EXTRACTION_EXAMPLES
                        )
                        st.session_state.medication_source_text = plan
                    else:
                        st.session_state.medications = []
                        st.session_state.medication_source_text = ""
                    st.session_state.medication_expanded_index = None

                    if plan.strip():
                        st.session_state.investigations = run_extraction(
                            plan, model_id, PROCEDURE_EXTRACTION_PROMPT, PROCEDURE_EXTRACTION_EXAMPLES
                        )
                        st.session_state.investigation_source_text = plan
                    else:
                        st.session_state.investigations = []
                        st.session_state.investigation_source_text = ""
                    st.session_state.investigation_expanded_index = None
                except Exception as e:
                    st.session_state.error = f"Failed to analyse: {e}"
            st.rerun()

    symptoms_tab, diagnoses_tab, medications_tab, investigations_tab = st.tabs(
        ["Symptoms", "Diagnoses", "Medications", "Investigations"], height="stretch"
    )

    with symptoms_tab:
        render_results_panel(
            state_key="symptoms",
            source_text_key="symptom_source_text",
            expanded_key="symptom_expanded_index",
            panel_title="Extracted Symptoms",
            item_name="symptom",
        )

    with diagnoses_tab:
        render_results_panel(
            state_key="diagnoses",
            source_text_key="diagnosis_source_text",
            expanded_key="diagnosis_expanded_index",
            panel_title="Extracted Diagnoses",
            item_name="diagnosis",
            enable_snomed_lookup=True,
        )

    with medications_tab:
        render_results_panel(
            state_key="medications",
            source_text_key="medication_source_text",
            expanded_key="medication_expanded_index",
            panel_title="Extracted Medications",
            item_name="medication",
        )

    with investigations_tab:
        render_results_panel(
            state_key="investigations",
            source_text_key="investigation_source_text",
            expanded_key="investigation_expanded_index",
            panel_title="Extracted Investigations",
            item_name="investigation",
        )

    if (
        st.session_state.symptoms
        or st.session_state.diagnoses
        or st.session_state.medications
        or st.session_state.investigations
    ):
        payload = build_entities_payload(
            st.session_state.symptoms,
            st.session_state.diagnoses,
            st.session_state.medications,
            st.session_state.investigations,
            st.session_state.encounter_datetime,
            st.session_state.original_text,
            st.session_state.encounter_id,
        )

        neo4j_configured = bool(NEO4J_URI and NEO4J_USERNAME and NEO4J_PASSWORD)
        dl_col, push_col = st.columns(2)
        with dl_col:
            st.download_button(
                "Generate Graph (JSON)",
                data=json.dumps(payload, indent=2),
                file_name=f"clinical_graph_{datetime.now().strftime('%Y-%m-%d')}.json",
                mime="application/json",
                use_container_width=True,
            )
        with push_col:
            if st.button("Push to Neo4j", use_container_width=True, disabled=not neo4j_configured):
                try:
                    with st.spinner("Pushing to Neo4j..."):
                        nodes, rels = push_encounter_to_neo4j(payload)
                        result = fetch_encounter_subgraph(st.session_state.encounter_id)
                        vg = from_neo4j(result)
                        vg.color_nodes(field="caption")
                        st.session_state.graph_viz_html = vg.render().data
                    st.session_state.neo4j_push_status = (
                        f"success: Pushed {nodes} nodes and {rels} relationships to Neo4j."
                    )
                except Exception as e:
                    st.session_state.neo4j_push_status = f"error: Failed to push to Neo4j: {e}"
            if not neo4j_configured:
                st.caption("Set NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD in .env to enable this.")

        if st.session_state.neo4j_push_status:
            kind, _, message = st.session_state.neo4j_push_status.partition(": ")
            (st.success if kind == "success" else st.error)(message)

        if st.session_state.graph_viz_html:
            st.subheader("Graph in Neo4j")
            st.iframe(st.session_state.graph_viz_html, height=500)

st.caption("🔐 Data is processed using Google Gemini API")
