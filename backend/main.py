#!/usr/bin/env python3
"""FastAPI backend for clinical consultation symptom extraction."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import langextract as lx
import json
import csv
from io import StringIO
from datetime import datetime
import os

# Load API key from environment
api_key = os.getenv('LANGEXTRACT_API_KEY')
if not api_key:
    raise ValueError("LANGEXTRACT_API_KEY environment variable not set")

app = FastAPI(
    title="Clinical Consultation Analyzer",
    description="Extract medical symptoms from clinical consultation text"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["localhost:3000", "http://localhost:3000", "127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractionRequest(BaseModel):
    text: str
    model_id: str = "gemini-3.6-flash"

class ExtractionResponse(BaseModel):
    status: str
    symptoms: list
    count: int

class ExportRequest(BaseModel):
    symptoms: list
    text: str = None

class SymptomAttribute(BaseModel):
    body_part: str = None
    severity: str = None
    duration: str = None

class Symptom(BaseModel):
    text: str
    attributes: dict
    position: dict = None

# Define extraction task
EXTRACTION_PROMPT = """Extract all medical symptoms mentioned in this clinical consultation.
For each symptom, identify:
- The exact symptom name as mentioned in the text
- The body part or area affected (if mentioned)
- The severity or duration (if mentioned)

Use exact text from the document. Do not paraphrase or combine symptoms.
List symptoms in the order they appear in the text."""

# Few-shot examples
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

@app.get("/")
def root():
    return {
        "message": "Clinical Consultation Symptom Extractor",
        "endpoints": {
            "POST /extract": "Extract symptoms from clinical text",
            "POST /export-csv": "Export extracted symptoms as CSV"
        }
    }

@app.post("/extract", response_model=ExtractionResponse)
async def extract_symptoms(request: ExtractionRequest):
    """Extract symptoms from clinical consultation text."""

    if not request.text or len(request.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text must be at least 10 characters")

    try:
        # Run extraction
        result = lx.extract(
            text_or_documents=request.text,
            prompt_description=EXTRACTION_PROMPT,
            examples=EXTRACTION_EXAMPLES,
            model_id=request.model_id,
            extraction_passes=1,
            max_workers=1,
        )

        # Format symptoms for response
        symptoms = []
        for extraction in result.extractions:
            symptom = {
                "text": extraction.extraction_text,
                "attributes": extraction.attributes or {},
                "position": {
                    "start": extraction.char_interval.start_pos if extraction.char_interval else None,
                    "end": extraction.char_interval.end_pos if extraction.char_interval else None
                } if extraction.char_interval else None
            }
            symptoms.append(symptom)

        # Store result for later use
        app.last_result = result
        app.last_text = request.text
        app.last_symptoms = symptoms

        return ExtractionResponse(
            status="success",
            symptoms=symptoms,
            count=len(symptoms)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.post("/export-csv")
async def export_csv(request: ExportRequest):
    """Export edited symptoms as CSV for Neo4j ingestion."""

    if not request.symptoms:
        raise HTTPException(status_code=400, detail="No symptoms provided for export.")

    try:
        # Create CSV buffer
        output = StringIO()

        # Define CSV headers for Neo4j ingestion
        headers = [
            "symptom_id",
            "symptom_text",
            "body_part",
            "severity",
            "duration",
            "timestamp"
        ]

        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()

        # Write symptom rows
        timestamp = datetime.now().isoformat()
        for idx, symptom in enumerate(request.symptoms, 1):
            writer.writerow({
                "symptom_id": f"symptom_{idx}",
                "symptom_text": symptom.get("text", ""),
                "body_part": symptom.get("attributes", {}).get("body_part"),
                "severity": symptom.get("attributes", {}).get("severity"),
                "duration": symptom.get("attributes", {}).get("duration"),
                "timestamp": timestamp
            })

        csv_content = output.getvalue()

        return {
            "status": "success",
            "filename": "symptoms.csv",
            "content": csv_content,
            "rows": len(request.symptoms)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}")

@app.post("/visualize")
async def visualize():
    """Generate HTML visualization of extracted symptoms."""

    if not hasattr(app, 'last_result') or not hasattr(app, 'last_text'):
        raise HTTPException(status_code=400, detail="No extraction results available. Run /extract first.")

    try:
        # Create annotated HTML
        text = app.last_text
        symptoms = app.last_symptoms

        # Build highlighted HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Symptom Visualization</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .text-container {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            line-height: 1.8;
            border-left: 4px solid #4CAF50;
        }}
        .symptom-highlight {{
            background: #ffeb3b;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
            cursor: pointer;
        }}
        .symptoms-list {{
            margin: 20px 0;
        }}
        .symptom-item {{
            background: #f0f7ff;
            padding: 12px;
            margin: 8px 0;
            border-left: 4px solid #2196F3;
            border-radius: 4px;
        }}
        .symptom-item h4 {{
            margin: 0 0 8px 0;
            color: #1976D2;
        }}
        .attribute {{
            font-size: 0.9em;
            color: #555;
            margin: 4px 0;
        }}
        .attribute-label {{
            font-weight: bold;
            color: #333;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Clinical Consultation Analysis</h1>

        <h2>Annotated Text</h2>
        <div class="text-container">
"""

        # Sort symptoms by position for highlighting
        sorted_symptoms = sorted(
            [s for s in symptoms if s["position"]],
            key=lambda x: x["position"]["start"]
        )

        # Build highlighted text
        if sorted_symptoms:
            last_pos = 0
            for symptom in sorted_symptoms:
                start = symptom["position"]["start"]
                end = symptom["position"]["end"]

                # Add text before highlight
                html_content += text[last_pos:start]

                # Add highlighted symptom
                html_content += f'<span class="symptom-highlight">{text[start:end]}</span>'

                last_pos = end

            # Add remaining text
            html_content += text[last_pos:]
        else:
            html_content += text

        html_content += """
        </div>

        <h2>Extracted Symptoms</h2>
        <div class="symptoms-list">
"""

        # Add symptom details
        for idx, symptom in enumerate(symptoms, 1):
            html_content += f"""
            <div class="symptom-item">
                <h4>{idx}. {symptom["text"]}</h4>
"""
            if symptom["attributes"]:
                for key, value in symptom["attributes"].items():
                    if value:
                        html_content += f'<div class="attribute"><span class="attribute-label">{key.replace("_", " ").title()}:</span> {value}</div>'

            html_content += """
            </div>
"""

        html_content += """
        </div>
    </div>
</body>
</html>
"""

        return {
            "status": "success",
            "html": html_content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visualization failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
