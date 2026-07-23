# Clinical Consultation Analyzer - Setup Guide

A full-stack web application for extracting medical symptoms from clinical consultation text using AI. Built with React, FastAPI, and LangExtract.

## 🎯 Features

- **Text Input**: Paste clinical consultation notes
- **AI-Powered Extraction**: Automatically extracts symptoms using Google Gemini API
- **Interactive Results**: View extracted symptoms with attributes (body part, severity, duration)
- **Visualization**: See symptoms highlighted in the original text
- **CSV Export**: Export results in Neo4j-compatible CSV format

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+ and npm
- Google Gemini API key (from https://aistudio.google.com/app/apikey)

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd /Users/jamesroberts/Downloads/GraphGen/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
cat > .env << EOF
LANGEXTRACT_API_KEY=your-gemini-api-key-here
EOF

# Run FastAPI server
python -m uvicorn main:app --reload --port 8000
```

The backend will be available at: **http://localhost:8000**

API Documentation: http://localhost:8000/docs

### 2. Frontend Setup

In a **new terminal**:

```bash
cd /Users/jamesroberts/Downloads/GraphGen/frontend

# Install dependencies
npm install

# Start React development server
REACT_APP_API_URL=http://localhost:8000 npm start
```

The frontend will open at: **http://localhost:3000**

## 📊 API Endpoints

### Extract Symptoms
```bash
POST /extract
Content-Type: application/json

{
  "text": "Your clinical consultation text here",
  "model_id": "gemini-3.6-flash"
}

Response:
{
  "status": "success",
  "symptoms": [
    {
      "text": "persistent cough",
      "attributes": {
        "body_part": "chest",
        "severity": "persistent",
        "duration": "3 weeks"
      },
      "position": {"start": 87, "end": 103}
    }
  ],
  "count": 10
}
```

### Export as CSV
```bash
POST /export-csv
Content-Type: application/json

{
  "text": "Your clinical consultation text here"
}

Response:
{
  "status": "success",
  "filename": "symptoms.csv",
  "content": "CSV content here...",
  "rows": 10
}
```

### Generate Visualization
```bash
POST /visualize

Response:
{
  "status": "success",
  "html": "<html>...</html>"
}
```

## 🔧 Configuration

### Backend Environment Variables

Create `backend/.env`:
```
LANGEXTRACT_API_KEY=your-gemini-api-key
```

### Frontend Environment Variables

Create `frontend/.env`:
```
REACT_APP_API_URL=http://localhost:8000
```

## 📁 Project Structure

```
GraphGen/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt         # Python dependencies
│   └── .env                     # API key (git-ignored)
├── frontend/
│   ├── src/
│   │   ├── App.js             # Main React component
│   │   ├── App.css            # Application styles
│   │   ├── index.js           # Entry point
│   │   └── index.css          # Global styles
│   ├── public/
│   │   └── index.html         # HTML template
│   ├── package.json           # Dependencies
│   └── .env                   # Frontend config
└── APP_SETUP.md               # This file
```

## 💻 Usage

1. **Start the application** (follow Quick Start above)

2. **Input clinical text**:
   - Go to the Input tab
   - Paste your clinical consultation notes
   - Click "Extract Symptoms"

3. **View results**:
   - Switch to Results tab to see extracted symptoms
   - Click symptoms to expand and view attributes
   - Results include body part, severity, and duration

4. **Visualize**:
   - Switch to Visualization tab
   - See symptoms highlighted in original text
   - Interactive HTML showing precise locations

5. **Export**:
   - Click "Export as CSV" button
   - Download symptoms in Neo4j-compatible format
   - Includes: symptom_id, text, attributes, position, timestamp

## 📊 CSV Export Format (Neo4j Compatible)

The CSV export includes these columns:
- `symptom_id`: Unique identifier (symptom_1, symptom_2, etc.)
- `symptom_text`: The symptom as extracted
- `body_part`: Affected body area
- `severity`: Severity level if mentioned
- `duration`: How long symptom persists
- `position_start`: Start position in text
- `position_end`: End position in text
- `timestamp`: When extraction was performed

### Neo4j Import Example

```cypher
LOAD CSV WITH HEADERS FROM 'file:///symptoms.csv' AS row
CREATE (s:Symptom {
  id: row.symptom_id,
  text: row.symptom_text,
  body_part: row.body_part,
  severity: row.severity,
  duration: row.duration,
  extracted_at: row.timestamp
})
```

## 🐛 Troubleshooting

### "API key not found" error
- Verify `LANGEXTRACT_API_KEY` is set in `backend/.env`
- Check key is valid at https://aistudio.google.com/app/apikey

### CORS errors in frontend
- Ensure backend is running on port 8000
- Check `REACT_APP_API_URL` environment variable
- Verify CORS is enabled in `main.py`

### Port already in use
- Backend: `python -m uvicorn main:app --port 8001`
- Frontend: `PORT=3001 npm start`

### Extraction is slow
- Using free tier Gemini API has rate limits
- Consider upgrading to paid plan for faster responses
- Check API quota at https://ai.google.dev/

## 🔒 Security Notes

- **Never commit `.env` files** to version control
- Store API keys in environment variables or secure vaults
- The application is intended for internal use
- Clinical data may be sensitive - review privacy policies

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [LangExtract GitHub](https://github.com/google/langextract)
- [Google Gemini API](https://ai.google.dev/)
- [Neo4j Documentation](https://neo4j.com/docs/)

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review API logs: `http://localhost:8000/docs`
3. Check browser console for frontend errors (F12)
4. Verify all services are running (backend on 8000, frontend on 3000)

## 📝 Next Steps

1. **Customize extraction prompt**: Edit `EXTRACTION_PROMPT` in `backend/main.py`
2. **Add more attributes**: Update extraction examples and CSV columns
3. **Integrate Neo4j**: Connect to your Neo4j database for graph creation
4. **Add authentication**: Implement user login if needed
5. **Deploy**: Use Docker, AWS, Heroku, or your preferred platform

---

Built with ❤️ using React, FastAPI, and Google Gemini API
