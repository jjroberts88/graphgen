# Clinical Consultation Analyzer

A Streamlit application for extracting medical symptoms from clinical consultation notes using LLMs.

## Features

- **Structured data entry**: History, Examination, Diagnosis, and Plan fields
- **LLM-powered extraction**: Automatically extracts symptoms from clinical text
- **Interactive results**: Edit, delete, and add symptoms to the extracted results
- **Source highlighting**: View exactly where each symptom was found in the original text
- **CSV export**: Export reviewed symptoms as CSV for further analysis or Neo4j ingestion

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

2. **Click "Analyse"** to extract symptoms using the LLM

3. **Review and edit** the results on the right panel:
   - Click the 📍 icon to see where each symptom appears in the original text
   - Use ✕ to delete unwanted symptoms
   - Type to add new symptoms

4. **Click "Generate Graph (CSV)"** to download the reviewed symptoms

## Security Notes

- **Never commit `.env` files** - Use `.env.example` as a template
- API keys should be managed through environment variables only
- Sensitive data (`.env`, credentials) are in `.gitignore`

## Project Structure

```
GraphGen/
├── streamlit_app.py            # Main application (UI + extraction + CSV export)
├── requirements-streamlit.txt  # App dependencies
├── .env.example                # Environment template
└── .gitignore                  # Git exclusions
```
