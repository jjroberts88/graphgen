#!/usr/bin/env python3
"""Streamlit app for clinical consultation symptom extraction."""

import json
import os
from datetime import datetime
from pathlib import Path

import langextract as lx
import streamlit as st
from dotenv import load_dotenv

# Look for a .env at the project root first, then fall back to backend/.env
# so the app works without extra setup for anyone who already had the
# FastAPI backend configured.
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env", override=False)

API_KEY = os.getenv("LANGEXTRACT_API_KEY")

DEFAULT_MODEL_ID = "gemini-3.6-flash"

EXTRACTION_PROMPT = """Extract all medical symptoms mentioned in this clinical consultation.
For each symptom, identify:
- The exact symptom name as mentioned in the text
- The body part or area affected (if mentioned)
- The severity or duration (if mentioned)

Use exact text from the document. Do not paraphrase or combine symptoms.
List symptoms in the order they appear in the text."""

EXTRACTION_EXAMPLES = [
    lx.data.ExampleData(
        text="""Patient reports persistent headache that started 2 days ago.
        She also complains of mild fever and body aches. Additionally,
        the patient has noticed a sore throat.""",
        extractions=[
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="persistent headache",
                attributes={
                    "body_part": "head",
                    "severity": "persistent",
                    "duration": "started 2 days ago",
                },
            ),
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="mild fever",
                attributes={
                    "body_part": "systemic",
                    "severity": "mild",
                    "duration": None,
                },
            ),
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="body aches",
                attributes={
                    "body_part": "body",
                    "severity": None,
                    "duration": None,
                },
            ),
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="sore throat",
                attributes={
                    "body_part": "throat",
                    "severity": None,
                    "duration": None,
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


SAMPLE_CASES = {
    "Community-acquired pneumonia": {
        "history": (
            "68-year-old male presents with a 3-day history of productive cough with "
            "green sputum, fever, and increasing shortness of breath. He describes "
            "right-sided pleuritic chest pain that worsens on deep inspiration. Reports "
            "feeling generally unwell with reduced appetite. No recent travel. Past "
            "medical history of type 2 diabetes."
        ),
        "examination": (
            "Temperature 38.6C, respiratory rate 24/min, oxygen saturation 93% on room "
            "air, heart rate 104 bpm, blood pressure 118/76. Reduced breath sounds and "
            "coarse crackles at the right lower lung base. Dullness to percussion over "
            "the same area. No peripheral oedema."
        ),
        "diagnosis": (
            "Likely community-acquired pneumonia, probable diagnosis pending chest "
            "X-ray. Type 2 diabetes, chronic, well controlled."
        ),
        "plan": (
            "Start empirical oral antibiotics (amoxicillin), arrange chest X-ray and "
            "bloods including CRP and blood cultures. Advise safety-net for worsening "
            "breathlessness. Review in 48 hours or sooner if deteriorating."
        ),
    },
    "Migraine": {
        "history": (
            "27-year-old female with a 1-day history of severe, throbbing left-sided "
            "headache associated with photophobia, phonophobia, and nausea. Reports "
            "similar episodes roughly once a month, often triggered by poor sleep and "
            "stress. No visual aura this episode. No head injury."
        ),
        "examination": (
            "Alert and oriented, in obvious discomfort. Neurological examination "
            "including cranial nerves, tone, power, reflexes, and coordination all "
            "normal. No neck stiffness or photophobia signs on examination. Fundoscopy "
            "normal."
        ),
        "diagnosis": ("Migraine without aura, recurrent, probable diagnosis based on history."),
        "plan": (
            "Advise rest in a dark, quiet room, hydration, and simple analgesia plus "
            "an antiemetic if needed. Discuss migraine triggers and consider "
            "prophylaxis if frequency increases. Provide headache diary and follow-up "
            "in 4 weeks."
        ),
    },
    "Suspected appendicitis": {
        "history": (
            "19-year-old male with a 12-hour history of central abdominal pain that "
            "has migrated to the right iliac fossa. Associated with nausea, one "
            "episode of vomiting, and loss of appetite. No diarrhoea. Pain worse on "
            "movement and coughing."
        ),
        "examination": (
            "Temperature 37.8C, heart rate 96 bpm. Abdomen tender in the right iliac "
            "fossa with guarding and rebound tenderness. Rovsing's sign positive. "
            "Bowel sounds present. No masses palpable."
        ),
        "diagnosis": (
            "Query early appendicitis - suspected, referred for surgical review. "
            "Differential includes mesenteric adenitis."
        ),
        "plan": (
            "Urgent surgical referral, keep nil by mouth, IV fluids, bloods including "
            "FBC and CRP, and urgent abdominal ultrasound or CT if diagnosis unclear. "
            "Analgesia as required."
        ),
    },
    "Hypertension follow-up": {
        "history": (
            "54-year-old female attending for routine hypertension review. Feels well "
            "with no headaches, chest pain, or visual disturbance. Reports good "
            "compliance with current antihypertensive medication. No new symptoms "
            "since last visit."
        ),
        "examination": (
            "Blood pressure 138/86 (repeat 136/84), heart rate 72 bpm regular. Heart "
            "sounds normal, chest clear, no peripheral oedema. BMI 27."
        ),
        "diagnosis": ("Chronic hypertension, well controlled on current medication."),
        "plan": (
            "Continue current antihypertensive regimen, reinforce lifestyle advice on "
            "diet, exercise, and salt intake. Routine bloods (U&E) and repeat review "
            "in 6 months."
        ),
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
# save_encounter_to_graph). `type` values ("Presentation", "Diagnosis") are
# schema.json entity labels, used directly as Neo4j node labels there — so
# they must stay capitalized exactly as in schema.json.
# No Patient/Encounter wrapper here (GraphGen doesn't collect that metadata),
# and no relationships between entities: schema.json only defines
# Encounter-scoped relationships (e.g. Encounter-[PRESENTED_WITH]->Presentation),
# and there's no Encounter node in this app's scope to anchor them to.
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
    symptoms: list[dict], diagnoses: list[dict], encounter_datetime: datetime, clinical_notes: str
) -> dict:
    encounter_id = "encounter-1"
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

    relationships = [
        {"type": "PRESENTED_WITH", "source": encounter_id, "target": entity["id"]} for entity in presentations
    ] + [
        {"type": "DIAGNOSED_WITH", "source": encounter_id, "target": entity["id"]} for entity in diagnosis_entities
    ]

    return {"entities": [encounter] + presentations + diagnosis_entities, "relationships": relationships}


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


def render_results_panel(state_key, source_text_key, expanded_key, panel_title, item_name):
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

        attributes = item.get("attributes") or {}
        attr_bits = [f"**{k.replace('_', ' ').title()}:** {v}" for k, v in attributes.items() if v]
        if attr_bits:
            st.caption(" · ".join(attr_bits))

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


st.set_page_config(page_title="Clinical Consultation Analyzer", page_icon="🏥", layout="wide")

if "symptoms" not in st.session_state:
    st.session_state.symptoms = []
if "original_text" not in st.session_state:
    st.session_state.original_text = ""
if "symptom_expanded_index" not in st.session_state:
    st.session_state.symptom_expanded_index = None
if "diagnoses" not in st.session_state:
    st.session_state.diagnoses = []
if "diagnosis_source_text" not in st.session_state:
    st.session_state.diagnosis_source_text = ""
if "diagnosis_expanded_index" not in st.session_state:
    st.session_state.diagnosis_expanded_index = None
if "error" not in st.session_state:
    st.session_state.error = ""
if "encounter_datetime" not in st.session_state:
    st.session_state.encounter_datetime = None

st.title("🏥 Clinical Data Entry")
st.caption("Enter clinical information and extract symptoms")

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
        st.session_state.history = case["history"]
        st.session_state.examination = case["examination"]
        st.session_state.diagnosis = case["diagnosis"]
        st.session_state.plan = case["plan"]
        st.rerun()

left, center, right = st.columns([2, 0.7, 2.3])

with left:
    st.subheader("History")
    history = st.text_area("History", key="history", placeholder="Enter patient history...", height=120, label_visibility="collapsed")

    st.subheader("Examination")
    examination = st.text_area("Examination", key="examination", placeholder="Enter examination findings...", height=120, label_visibility="collapsed")

    st.subheader("Diagnosis")
    diagnosis = st.text_area("Diagnosis", key="diagnosis", placeholder="Enter diagnosis...", height=120, label_visibility="collapsed")

    st.subheader("Plan")
    plan = st.text_area("Plan", key="plan", placeholder="Enter treatment plan...", height=120, label_visibility="collapsed")

with center:
    model_id = st.text_input("Model ID", value=DEFAULT_MODEL_ID)
    st.caption(
        "Note: the vendored langextract library's documented default is "
        "`gemini-3.5-flash` — double-check this ID is valid for your key."
    )
    analyse_clicked = st.button("Analyse", use_container_width=True, type="primary")

with right:
    if analyse_clicked:
        all_text = f"History: {history}\n\nExamination: {examination}\n\nDiagnosis: {diagnosis}\n\nPlan: {plan}"

        if not all_text.strip() or len(all_text) < 50:
            st.session_state.error = "Please fill in the clinical data fields"
        else:
            st.session_state.error = ""
            with st.spinner("Analysing..."):
                try:
                    st.session_state.encounter_datetime = datetime.now()
                    st.session_state.symptoms = run_extraction(
                        all_text, model_id, EXTRACTION_PROMPT, EXTRACTION_EXAMPLES
                    )
                    st.session_state.original_text = all_text
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
                except Exception as e:
                    st.session_state.error = f"Failed to analyse: {e}"
            st.rerun()

    symptoms_tab, diagnoses_tab = st.tabs(["Symptoms", "Diagnoses"])

    with symptoms_tab:
        render_results_panel(
            state_key="symptoms",
            source_text_key="original_text",
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
        )

    if st.session_state.symptoms or st.session_state.diagnoses:
        payload = build_entities_payload(
            st.session_state.symptoms,
            st.session_state.diagnoses,
            st.session_state.encounter_datetime,
            st.session_state.original_text,
        )
        st.download_button(
            "Generate Graph (JSON)",
            data=json.dumps(payload, indent=2),
            file_name=f"clinical_graph_{datetime.now().strftime('%Y-%m-%d')}.json",
            mime="application/json",
            use_container_width=True,
        )

st.caption("🔐 Data is processed using Google Gemini API")
