import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [history, setHistory] = useState('');
  const [examination, setExamination] = useState('');
  const [diagnosis, setDiagnosis] = useState('');
  const [plan, setPlan] = useState('');

  const [symptoms, setSymptoms] = useState([]);
  const [newSymptom, setNewSymptom] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [originalText, setOriginalText] = useState('');
  const [expandedSourceIndex, setExpandedSourceIndex] = useState(null);

  const handleAnalyse = async () => {
    const allText = `History: ${history}\n\nExamination: ${examination}\n\nDiagnosis: ${diagnosis}\n\nPlan: ${plan}`;

    if (!allText.trim() || allText.length < 50) {
      setError('Please fill in the clinical data fields');
      return;
    }

    setLoading(true);
    setError('');
    setSymptoms([]);
    setExpandedSourceIndex(null);

    try {
      const response = await axios.post(`${API_URL}/extract`, {
        text: allText,
        model_id: 'gemini-3.6-flash'
      });

      setSymptoms(response.data.symptoms || []);
      setOriginalText(allText);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyse. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSymptom = () => {
    if (newSymptom.trim()) {
      setSymptoms([...symptoms, { text: newSymptom, attributes: {} }]);
      setNewSymptom('');
    }
  };

  const handleDeleteSymptom = (index) => {
    setSymptoms(symptoms.filter((_, i) => i !== index));
  };

  const getSourceContext = (symptom) => {
    if (!symptom.position || !originalText) {
      return null;
    }

    const { start, end } = symptom.position;
    const contextPadding = 100;
    const contextStart = Math.max(0, start - contextPadding);
    const contextEnd = Math.min(originalText.length, end + contextPadding);

    const beforeText = originalText.substring(contextStart, start);
    const highlightedText = originalText.substring(start, end);
    const afterText = originalText.substring(end, contextEnd);

    return { beforeText, highlightedText, afterText };
  };

  const handleGenerateGraph = async () => {
    if (symptoms.length === 0) {
      setError('No symptoms to export');
      return;
    }

    try {
      const allText = `History: ${history}\n\nExamination: ${examination}\n\nDiagnosis: ${diagnosis}\n\nPlan: ${plan}`;

      const response = await axios.post(`${API_URL}/export-csv`, {
        symptoms: symptoms,
        text: allText
      });

      const blob = new Blob([response.data.content], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `clinical_data_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Failed to generate CSV');
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🏥 Clinical Data Entry</h1>
        <p>Enter clinical information and extract symptoms</p>
      </header>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError('')} className="close-btn">✕</button>
        </div>
      )}

      <div className="main-container">
        {/* Left Side - Data Entry */}
        <div className="left-panel">
          <div className="data-box">
            <h2>History</h2>
            <textarea
              value={history}
              onChange={(e) => setHistory(e.target.value)}
              placeholder="Enter patient history..."
              className="data-textarea"
            />
          </div>

          <div className="data-box">
            <h2>Examination</h2>
            <textarea
              value={examination}
              onChange={(e) => setExamination(e.target.value)}
              placeholder="Enter examination findings..."
              className="data-textarea"
            />
          </div>

          <div className="data-box">
            <h2>Diagnosis</h2>
            <textarea
              value={diagnosis}
              onChange={(e) => setDiagnosis(e.target.value)}
              placeholder="Enter diagnosis..."
              className="data-textarea"
            />
          </div>

          <div className="data-box">
            <h2>Plan</h2>
            <textarea
              value={plan}
              onChange={(e) => setPlan(e.target.value)}
              placeholder="Enter treatment plan..."
              className="data-textarea"
            />
          </div>
        </div>

        {/* Center - Control Button */}
        <div className="center-panel">
          <button
            onClick={handleAnalyse}
            disabled={loading}
            className="btn-analyse"
          >
            {loading ? '⏳ Analysing...' : 'Analyse'}
          </button>
        </div>

        {/* Right Side - Output */}
        <div className="right-panel">
          {symptoms.length === 0 ? (
            <div className="empty-message">
              <p>Click "Analyse" to extract symptoms from the clinical data</p>
            </div>
          ) : (
            <div className="symptoms-section">
              <div className="symptoms-header">
                <h2>Extracted Symptoms</h2>
                <span className="count-badge">{symptoms.length}</span>
              </div>

              <div className="symptoms-list">
                {symptoms.map((symptom, index) => {
                  const sourceContext = getSourceContext(symptom);
                  const isExpanded = expandedSourceIndex === index;

                  return (
                    <div key={index} className="symptom-item">
                      <div className="symptom-header-row">
                        <span className="symptom-text">{symptom.text}</span>
                        <div className="symptom-actions">
                          {sourceContext && (
                            <button
                              onClick={() => setExpandedSourceIndex(isExpanded ? null : index)}
                              className="source-btn"
                              title="View source in original text"
                            >
                              📍
                            </button>
                          )}
                          <button
                            onClick={() => handleDeleteSymptom(index)}
                            className="delete-btn"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                      {isExpanded && sourceContext && (
                        <div className="source-context">
                          <div className="source-label">Source:</div>
                          <div className="source-text">
                            <span className="before">{sourceContext.beforeText}</span>
                            <span className="highlighted">{sourceContext.highlightedText}</span>
                            <span className="after">{sourceContext.afterText}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="add-symptom">
                <input
                  type="text"
                  value={newSymptom}
                  onChange={(e) => setNewSymptom(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddSymptom()}
                  placeholder="Add new symptom..."
                  className="symptom-input"
                />
                <button
                  onClick={handleAddSymptom}
                  className="btn-add"
                >
                  Add
                </button>
              </div>

              <button
                onClick={handleGenerateGraph}
                className="btn-generate"
              >
                Generate Graph (CSV)
              </button>
            </div>
          )}
        </div>
      </div>

      <footer className="footer">
        <p>🔐 Data is processed using Google Gemini API</p>
      </footer>
    </div>
  );
}

export default App;
