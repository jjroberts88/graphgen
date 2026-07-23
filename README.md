# Clinical Consultation Analyzer

A web-based application for extracting medical symptoms from clinical consultation notes using LLMs.

## Features

- **Split-screen interface**: Clinical data entry on the left, results on the right
- **LLM-powered extraction**: Automatically extracts symptoms from clinical text
- **Interactive results**: Edit, delete, and add symptoms to the extracted results
- **Source highlighting**: View exactly where each symptom was found in the original text
- **CSV export**: Export reviewed symptoms as CSV for further analysis or Neo4j ingestion

## Setup

### Prerequisites
- Python 3.9+
- Node.js 16+
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

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs on `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend runs on `http://localhost:3000`

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

## API Endpoints

- `POST /extract` - Extract symptoms from clinical text
- `POST /export-csv` - Export symptoms as CSV
- `POST /visualize` - Generate HTML visualization of extracted symptoms

## Security Notes

- **Never commit `.env` files** - Use `.env.example` as a template
- API keys should be managed through environment variables only
- Sensitive data (`.env`, credentials) are in `.gitignore`

## Project Structure

```
GraphGen/
├── backend/          # FastAPI backend
│   └── main.py      # Main application
├── frontend/        # React frontend
│   └── src/
│       ├── App.js   # Main component
│       └── App.css  # Styles
├── .env.example     # Environment template
└── .gitignore       # Git exclusions
```
