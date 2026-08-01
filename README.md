# Clinical Consultation Analyzer

A Streamlit application for extracting medical symptoms from clinical consultation notes using LLMs.

## Features

- **Structured data entry**: History, Examination, Diagnosis, and Plan fields
- **LLM-powered extraction**: Automatically extracts symptoms and diagnoses from clinical text
- **Interactive results**: Edit, delete, and add symptoms/diagnoses to the extracted results
- **Source highlighting**: View exactly where each item was found in the original text
- **JSON export**: Export reviewed symptoms and diagnoses as a JSON entities/relationships payload for Neo4j ingestion

## Setup

### Prerequisites
- Python 3.9+
- LangExtract API key

### 1. Environment Setup

Copy `.env.example` to `.env` and add your API key:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```
LANGEXTRACT_API_KEY=your_api_key_here
```

### 2. Install dependencies

```bash
pip install -r requirements-streamlit.txt
```

### 3. Run the app

```bash
streamlit run streamlit_app.py
```

The app runs on `http://localhost:8501`

## Usage

1. **Enter clinical data** in the 4 input boxes on the left:
   - History
   - Examination
   - Diagnosis
   - Plan

2. **Click "Analyse"** to extract symptoms and diagnoses using the LLM

3. **Review and edit** the results in the Symptoms/Diagnoses tabs on the right panel:
   - Click the 📍 icon to see where each item appears in the original text
   - Use ✕ to delete unwanted items
   - Type to add new items

4. **Click "Generate Graph (JSON)"** to download the reviewed symptoms and diagnoses

## Security Notes

- **Never commit `.env` files** - Use `.env.example` as a template
- API keys should be managed through environment variables only
- Sensitive data (`.env`, credentials) are in `.gitignore`

## Project Structure

```
GraphGen/
├── streamlit_app.py            # Main application (UI + extraction + JSON export)
├── requirements-streamlit.txt  # App dependencies
├── schema.json                 # Neo4j graph entity/relationship schema referenced by the JSON export
├── .env.example                # Environment template
└── .gitignore                  # Git exclusions
```
