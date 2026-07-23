#!/usr/bin/env python3
"""Extract symptoms from medical consultation documents."""

import os
if not os.getenv('LANGEXTRACT_API_KEY'):
    raise ValueError("LANGEXTRACT_API_KEY environment variable not set")

import langextract as lx

print("=" * 80)
print("MEDICAL SYMPTOM EXTRACTION")
print("=" * 80)

# Medical consultation document
medical_text = """
PATIENT CONSULTATION NOTES - Date: 2024-01-15

Chief Complaint: Patient presents with persistent cough and difficulty breathing

History of Present Illness:
Patient is a 45-year-old male who has been experiencing a dry cough for the past 3 weeks.
The cough is worse at night and disrupts sleep. He also reports shortness of breath,
especially during physical activity. Additionally, the patient complains of mild chest pain
when coughing and has noticed some fatigue over the past few days.

The patient denies fever but mentions experiencing occasional headaches.
He reports nasal congestion that started about 5 days ago, which may be related to
seasonal allergies. The patient also mentions feeling dizzy upon standing quickly.

Physical Examination:
Vital signs are within normal limits. Lung auscultation reveals some wheezing.
No signs of infection noted.

Assessment:
Likely viral upper respiratory infection with possible bronchospasm.
Recommend hydration, rest, and follow-up in one week if symptoms persist.
"""

print(f"\nMedical Document:\n{medical_text}\n")

# Define extraction task for symptoms
prompt = """Extract all medical symptoms mentioned in this consultation.
For each symptom, identify:
- The exact symptom name as mentioned in the text
- The body part or area affected (if mentioned)
- The severity or duration (if mentioned)

Use exact text from the document. Do not paraphrase or combine symptoms.
List symptoms in the order they appear in the text."""

# Provide high-quality examples to guide extraction
examples = [
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
                    "duration": "started 2 days ago"
                }
            ),
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="mild fever",
                attributes={
                    "body_part": "systemic",
                    "severity": "mild",
                    "duration": None
                }
            ),
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="body aches",
                attributes={
                    "body_part": "body",
                    "severity": None,
                    "duration": None
                }
            ),
            lx.data.Extraction(
                extraction_class="symptom",
                extraction_text="sore throat",
                attributes={
                    "body_part": "throat",
                    "severity": None,
                    "duration": None
                }
            ),
        ]
    )
]

print("=" * 80)
print("EXTRACTING SYMPTOMS...")
print("=" * 80)

try:
    result = lx.extract(
        text_or_documents=medical_text,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-3.6-flash",
        extraction_passes=1,
        max_workers=1,
    )

    print(f"\n✓ EXTRACTION COMPLETE!\n")
    print(f"Found {len(result.extractions)} symptoms:\n")
    print("-" * 80)

    for i, extraction in enumerate(result.extractions, 1):
        print(f"\n{i}. SYMPTOM: {extraction.extraction_text}")

        if extraction.attributes:
            print("   Details:")
            for key, value in extraction.attributes.items():
                if value:
                    print(f"   • {key.replace('_', ' ').title()}: {value}")

        if extraction.char_interval:
            print(f"   Position: [{extraction.char_interval.start_pos}:{extraction.char_interval.end_pos}]")

    print("\n" + "=" * 80)

    # Step 2: Save to JSONL
    print("\nSaving to JSONL...")
    lx.io.save_annotated_documents([result], output_name="medical_extraction_results.jsonl", output_dir=".")
    print("✓ Saved to medical_extraction_results.jsonl")

    # Step 3: Generate visualization
    print("\nGenerating visualization...")
    html_content = lx.visualize("medical_extraction_results.jsonl")
    with open("medical_visualization.html", "w") as f:
        if hasattr(html_content, 'data'):
            f.write(html_content.data)
        else:
            f.write(html_content)
    print("✓ Saved to medical_visualization.html")

    print("\n" + "=" * 80)
    print("FILES CREATED:")
    print("=" * 80)
    print("✓ medical_extraction_results.jsonl (structured data)")
    print("✓ medical_visualization.html (interactive visualization)")
    print("\nOpen medical_visualization.html in your browser to see the results!")
    print("=" * 80)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
