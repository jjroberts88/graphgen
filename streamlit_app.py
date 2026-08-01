#!/usr/bin/env python3
"""Streamlit app for clinical consultation symptom extraction."""

import csv
import os
from datetime import datetime
from io import StringIO
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


def build_csv(items: list[dict], id_prefix: str, text_field: str, attribute_fields: list[str]) -> str:
    output = StringIO()
    headers = [f"{id_prefix}_id", text_field, *attribute_fields, "timestamp"]
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()

    timestamp = datetime.now().isoformat()
    for idx, item in enumerate(items, 1):
        attributes = item.get("attributes", {})
        row = {f"{id_prefix}_id": f"{id_prefix}_{idx}", text_field: item.get("text", ""), "timestamp": timestamp}
        for field in attribute_fields:
            row[field] = attributes.get(field)
        writer.writerow(row)
    return output.getvalue()


def build_symptom_csv(symptoms: list[dict]) -> str:
    return build_csv(symptoms, "symptom", "symptom_text", ["body_part", "severity", "duration"])


def build_diagnosis_csv(diagnoses: list[dict]) -> str:
    return build_csv(diagnoses, "diagnosis", "diagnosis_text", ["status", "certainty"])


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


def render_results_panel(state_key, source_text_key, expanded_key, panel_title, item_name, csv_builder, csv_filename_prefix):
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

    csv_content = csv_builder(items)
    st.download_button(
        "Generate Graph (CSV)",
        data=csv_content,
        file_name=f"{csv_filename_prefix}_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"download_{state_key}",
    )


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
            csv_builder=build_symptom_csv,
            csv_filename_prefix="symptoms",
        )

    with diagnoses_tab:
        render_results_panel(
            state_key="diagnoses",
            source_text_key="diagnosis_source_text",
            expanded_key="diagnosis_expanded_index",
            panel_title="Extracted Diagnoses",
            item_name="diagnosis",
            csv_builder=build_diagnosis_csv,
            csv_filename_prefix="diagnoses",
        )

st.caption("🔐 Data is processed using Google Gemini API")
