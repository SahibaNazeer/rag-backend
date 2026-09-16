import React, { useState } from 'react';

function App() {
  const [file, setFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return alert('Pehle PDF file select karein');
    const formData = new FormData();
    formData.append('file', file);

    setUploadStatus('Processing PDF & Vector Embeddings...');
    try {
      const res = await fetch('http://127.0.0.1:8000/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      setUploadStatus(data.message);
    } catch (err) {
      setUploadStatus('Upload failed: ' + err.message);
    }
  };

  const handleQuery = async () => {
    if (!question) return alert('Sawal type karein');
    setLoading(true);
    setAnswer('');
    try {
      const res = await fetch('http://127.0.0.1:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Query failed');
      setAnswer(data.answer);
    } catch (err) {
      setAnswer('Error: ' + err.message);
    }
    setLoading(false);
  };

  return (
    <div style={{ padding: '30px', maxWidth: '700px', margin: 'auto', fontFamily: 'Arial' }}>
      <h2>RAG Application (Gemini + pgvector)</h2>

      <div style={{ border: '1px solid #ccc', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3>1. Upload PDF Document</h3>
        <input type="file" accept=".pdf" onChange={handleFileChange} />
        <button onClick={handleUpload} style={{ marginLeft: '10px', padding: '5px 15px' }}>Upload</button>
        <p><strong>Status:</strong> {uploadStatus}</p>
      </div>

      <div style={{ border: '1px solid #ccc', padding: '20px', borderRadius: '8px' }}>
        <h3>2. Ask Question from PDF</h3>
        <input 
          type="text" 
          value={question} 
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="PDF se related sawal pucho..." 
          style={{ width: '70%', padding: '8px' }}
        />
        <button onClick={handleQuery} style={{ marginLeft: '10px', padding: '8px 15px' }}>Submit</button>

        {loading && <p>Searching vector DB & generating response...</p>}
        {answer && (
          <div style={{ marginTop: '15px', background: '#f4f4f4', padding: '15px', borderRadius: '5px' }}>
            <h4>Answer:</h4>
            <p>{answer}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;