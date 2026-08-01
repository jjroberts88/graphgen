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


def run_extraction(text: str, model_id: str) -> list[dict]:
    result = lx.extract(
        text_or_documents=text,
        prompt_description=EXTRACTION_PROMPT,
        examples=EXTRACTION_EXAMPLES,
        model_id=model_id,
        extraction_passes=1,
        max_workers=1,
    )

    symptoms = []
    for extraction in result.extractions:
        symptoms.append(
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
    return symptoms


def build_csv(symptoms: list[dict]) -> str:
    output = StringIO()
    headers = ["symptom_id", "symptom_text", "body_part", "severity", "duration", "timestamp"]
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()

    timestamp = datetime.now().isoformat()
    for idx, symptom in enumerate(symptoms, 1):
        attributes = symptom.get("attributes", {})
        writer.writerow(
            {
                "symptom_id": f"symptom_{idx}",
                "symptom_text": symptom.get("text", ""),
                "body_part": attributes.get("body_part"),
                "severity": attributes.get("severity"),
                "duration": attributes.get("duration"),
                "timestamp": timestamp,
            }
        )
    return output.getvalue()


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


st.set_page_config(page_title="Clinical Consultation Analyzer", page_icon="🏥", layout="wide")

if "symptoms" not in st.session_state:
    st.session_state.symptoms = []
if "original_text" not in st.session_state:
    st.session_state.original_text = ""
if "expanded_index" not in st.session_state:
    st.session_state.expanded_index = None
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
                    st.session_state.symptoms = run_extraction(all_text, model_id)
                    st.session_state.original_text = all_text
                    st.session_state.expanded_index = None
                except Exception as e:
                    st.session_state.error = f"Failed to analyse: {e}"
            st.rerun()

    if not st.session_state.symptoms:
        st.info('Click "Analyse" to extract symptoms from the clinical data')
    else:
        st.subheader(f"Extracted Symptoms ({len(st.session_state.symptoms)})")

        for idx, symptom in enumerate(st.session_state.symptoms):
            text_col, source_col, delete_col = st.columns([6, 1, 1])
            text_col.markdown(f"**{symptom['text']}**")

            context = get_source_context(symptom, st.session_state.original_text)
            if context and source_col.button("📍", key=f"source_{idx}"):
                st.session_state.expanded_index = None if st.session_state.expanded_index == idx else idx

            if delete_col.button("✕", key=f"delete_{idx}"):
                st.session_state.symptoms.pop(idx)
                st.rerun()

            attributes = symptom.get("attributes") or {}
            attr_bits = [f"**{k.replace('_', ' ').title()}:** {v}" for k, v in attributes.items() if v]
            if attr_bits:
                st.caption(" · ".join(attr_bits))

            if context and st.session_state.expanded_index == idx:
                st.markdown(
                    f"Source: _{context['before']}_ "
                    f":orange[**{context['highlighted']}**] "
                    f"_{context['after']}_"
                )

            st.divider()

        with st.form("add_symptom_form", clear_on_submit=True):
            add_col, submit_col = st.columns([5, 1])
            new_symptom_text = add_col.text_input(
                "Add new symptom", placeholder="Add new symptom...", label_visibility="collapsed"
            )
            submitted = submit_col.form_submit_button("Add")
            if submitted and new_symptom_text.strip():
                st.session_state.symptoms.append(
                    {"text": new_symptom_text.strip(), "attributes": {}, "position": None}
                )
                st.rerun()

        csv_content = build_csv(st.session_state.symptoms)
        st.download_button(
            "Generate Graph (CSV)",
            data=csv_content,
            file_name=f"clinical_data_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.caption("🔐 Data is processed using Google Gemini API")
