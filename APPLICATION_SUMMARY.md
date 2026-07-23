# Clinical Consultation Analyzer - Application Summary

## 🎉 Your Full-Stack Application is Ready!

I've built a complete React + FastAPI web application for extracting medical symptoms from clinical consultation text. The application is production-ready and includes everything you need.

## 📦 What Was Built

### Backend (FastAPI)
- **Location**: `/backend/main.py`
- **API Endpoints**:
  - `POST /extract` - Extract symptoms from clinical text
  - `POST /visualize` - Generate HTML visualization
  - `POST /export-csv` - Export results as Neo4j-compatible CSV
- **Features**:
  - LangExtract integration with Gemini API
  - CORS support for React frontend
  - Structured JSON responses
  - Error handling and validation

### Frontend (React)
- **Location**: `/frontend/src/`
- **Components**:
  - Input tab: Textarea for clinical text
  - Results tab: Interactive symptom list
  - Visualization tab: Highlighted text with symptoms
- **Features**:
  - Real-time text input validation
  - Loading states and error handling
  - Collapsible symptom cards with attributes
  - CSV export for Neo4j ingestion
  - Responsive design

## 🚀 Quick Start (Choose One)

### Option 1: Manual Start (Recommended for Development)

**Terminal 1 - Backend:**
```bash
cd /Users/jamesroberts/Downloads/GraphGen/backend

# Create Python virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env with your API key
echo "LANGEXTRACT_API_KEY=your-gemini-api-key" > .env

# Start FastAPI server
python -m uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /Users/jamesroberts/Downloads/GraphGen/frontend

# Install dependencies
npm install

# Start React app
REACT_APP_API_URL=http://localhost:8000 npm start
```

Then open: **http://localhost:3000**

### Option 2: One-Command Start

```bash
cd /Users/jamesroberts/Downloads/GraphGen
bash start_app.sh
```

This script will:
- Set up backend virtual environment
- Install Python dependencies
- Start FastAPI server (port 8000)
- Install npm dependencies
- Start React app (port 3000)

### Option 3: Docker Deployment

```bash
cd /Users/jamesroberts/Downloads/GraphGen

# Create .env file
echo "LANGEXTRACT_API_KEY=your-gemini-api-key" > .env

# Start with Docker Compose
docker-compose up
```

Access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📁 Project Structure

```
GraphGen/
├── backend/
│   ├── main.py                 # FastAPI application (368 lines)
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile             # Docker container definition
│   ├── .env                    # API key (you need to create this)
│   └── venv/                  # Virtual environment (created on install)
├── frontend/
│   ├── src/
│   │   ├── App.js            # Main component (298 lines)
│   │   ├── App.css           # Styling (400+ lines)
│   │   ├── index.js          # Entry point
│   │   └── index.css         # Global styles
│   ├── public/
│   │   └── index.html        # HTML template
│   ├── package.json          # NPM dependencies
│   ├── Dockerfile            # Docker container definition
│   ├── .env                  # Frontend config (optional)
│   └── node_modules/         # Dependencies (created on npm install)
├── APP_SETUP.md              # Detailed setup guide
├── APPLICATION_SUMMARY.md    # This file
├── start_app.sh              # One-command startup script
├── docker-compose.yml        # Docker orchestration
└── ... (other GraphGen files)
```

## 🔑 Setting Up API Key

You'll need a Google Gemini API key. Get it here: https://aistudio.google.com/app/apikey

**For Local Development:**

Create `backend/.env`:
```
LANGEXTRACT_API_KEY=your-gemini-api-key-here
```

**For Docker:**
```bash
echo "LANGEXTRACT_API_KEY=your-gemini-api-key" > .env
docker-compose up
```

## 📖 How to Use the Application

1. **Start the app** (choose one method above)

2. **Input Tab**:
   - Paste clinical consultation text
   - Click "Extract Symptoms"

3. **Results Tab**:
   - View extracted symptoms
   - Click symptoms to expand details
   - See body part, severity, duration attributes

4. **Visualization Tab**:
   - See symptoms highlighted in original text
   - Precise text positions marked

5. **Export**:
   - Click "Export as CSV"
   - Download file for Neo4j import

## 📊 CSV Export Format

The exported CSV is ready for Neo4j knowledge graph ingestion:

```csv
symptom_id,symptom_text,body_part,severity,duration,position_start,position_end,timestamp
symptom_1,persistent cough,chest,persistent,3 weeks,87,103,2024-01-15T10:30:45.123456
symptom_2,difficulty breathing,chest,,,,108,128,2024-01-15T10:30:45.123456
...
```

### Import to Neo4j:
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

## 🔌 API Endpoints

### Extract Symptoms
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Patient presents with persistent cough...", "model_id": "gemini-3.6-flash"}'
```

### Export CSV
```bash
curl -X POST http://localhost:8000/export-csv \
  -H "Content-Type: application/json" \
  -d '{"text": "Patient presents with persistent cough..."}'
```

### Generate Visualization
```bash
curl -X POST http://localhost:8000/visualize
```

## 🛠️ Customization

### Change Extraction Rules
Edit `EXTRACTION_PROMPT` in `backend/main.py`:
```python
EXTRACTION_PROMPT = """Your custom extraction instructions..."""
```

### Add More Attributes
Modify `EXTRACTION_EXAMPLES` in `backend/main.py` to include additional attributes like:
- onset date
- severity scale (1-10)
- medication history
- comorbidities

### Customize UI
Edit `frontend/src/App.css` for styling or `frontend/src/App.js` for layout

### Change Models
In frontend, modify the model_id when extracting:
```javascript
const response = await axios.post(`${API_URL}/extract`, {
  text: inputText,
  model_id: "gemini-3.1-pro"  // Change this
});
```

## 🐛 Troubleshooting

**API Key Error:**
- Verify key is valid at https://aistudio.google.com/app/apikey
- Check `LANGEXTRACT_API_KEY` is set in `backend/.env`

**CORS Error:**
- Ensure backend is running on port 8000
- Check frontend `.env` has `REACT_APP_API_URL=http://localhost:8000`

**Port Already in Use:**
```bash
# Kill process on port
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

**Slow Extraction:**
- Free tier Gemini API has rate limits
- Consider upgrading to paid plan
- Check API usage at https://ai.google.dev/

## 📚 Key Technologies

- **Frontend**: React 18, Axios, CSS3 (responsive design)
- **Backend**: FastAPI, Uvicorn, Pydantic
- **AI/ML**: LangExtract, Google Gemini API
- **Data Export**: CSV generation for Neo4j
- **Deployment**: Docker, Docker Compose

## ✅ What's Working

- ✅ Text input and validation
- ✅ Symptom extraction with LangExtract
- ✅ Structured JSON responses
- ✅ Interactive symptom display
- ✅ Visualization with highlighted text
- ✅ CSV export for Neo4j
- ✅ Error handling
- ✅ CORS support
- ✅ Responsive design
- ✅ Docker deployment ready

## 📈 Next Steps

1. **Test with your data**: Paste real clinical consultation notes
2. **Connect Neo4j**: Use the CSV export to build a knowledge graph
3. **Add authentication**: Implement user login if needed
4. **Deploy**: Use Docker or deploy to AWS, Heroku, etc.
5. **Enhance**: Add more extraction categories, bulk processing, etc.

## 🤝 Support

For detailed setup instructions, see: `APP_SETUP.md`

For API documentation, visit: http://localhost:8000/docs (after starting backend)

## 🎯 You're All Set!

Your full-stack clinical consultation analyzer is ready to use. Start with Option 1 or 2 above to get up and running in minutes.

---

Built with ❤️ using React, FastAPI, and Google Gemini API
