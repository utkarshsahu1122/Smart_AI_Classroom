import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE } from '../config'

function FacultyDashboard() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [dragover, setDragover] = useState(false)
  const [mcqWeight, setMcqWeight] = useState(70)
  const [fillWeight, setFillWeight] = useState(30)
  const fileInputRef = useRef(null)
  const navigate = useNavigate()

  const handleFileChange = (e) => {
    const selected = e.target.files[0]
    if (selected && selected.type === 'application/pdf') {
      setFile(selected)
      setError('')
    } else {
      setError('Please select a valid PDF file')
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragover(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped && dropped.type === 'application/pdf') {
      setFile(dropped)
      setError('')
    } else {
      setError('Please drop a valid PDF file')
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a PDF file first')
      return
    }

    setUploading(true)
    setError('')

    const formData = new FormData()
    formData.append('pdf_file', file)
    formData.append('mcq_weight', mcqWeight)
    formData.append('fill_weight', fillWeight)

    try {
      const res = await fetch(`${API_BASE}/api/faculty/upload`, {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()

      if (data.success) {
        navigate(`/faculty/session/${data.session_code}`)
      } else {
        setError(data.error || 'Upload failed')
      }
    } catch (err) {
      setError('Backend not connected. Please try again later.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Faculty Dashboard</h1>
        <p>Upload course material to generate an AI-powered quiz session</p>
      </div>

      {error && <div className="alert alert-error">⚠️ {error}</div>}

      {uploading ? (
        <div className="glass-card">
          <div className="spinner-overlay">
            <div className="spinner"></div>
            <p className="spinner-text">Processing PDF & generating questions with Gemini AI...</p>
            <p className="text-muted" style={{ fontSize: '0.8rem' }}>This may take 15–30 seconds depending on PDF length</p>
          </div>
        </div>
      ) : (
        <div className="glass-card">
          <div
            className={`upload-zone ${dragover ? 'dragover' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragover(true) }}
            onDragLeave={() => setDragover(false)}
            onDrop={handleDrop}
          >
            <div className="upload-icon">📄</div>
            <p className="upload-text">
              <strong>Click to browse</strong> or drag & drop your PDF here
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
            />
            {file && (
              <p className="file-selected">✅ {file.name} ({(file.size / 1024).toFixed(0)} KB)</p>
            )}
          </div>

          {file && (
            <div className="weight-settings mt-2" style={{ display: 'flex', gap: '2rem', justifyContent: 'center', alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <div className="form-group" style={{ flex: '1', minWidth: '160px', maxWidth: '220px', textAlign: 'left', marginBottom: '0' }}>
                <label style={{ fontSize: '0.85rem', fontWeight: 'bold', letterSpacing: '0.5px', textTransform: 'uppercase', display: 'block', marginBottom: '0.5rem', color: '#a0aec0' }}>MCQs Weight (%)</label>
                <input 
                  type="number" 
                  className="input" 
                  style={{ width: '100%', padding: '0.7rem', borderRadius: '6px', border: '1px solid #4a5568', backgroundColor: '#2d3748', color: '#fff' }}
                  value={mcqWeight} 
                  onChange={(e) => {
                    let val = parseInt(e.target.value) || 0;
                    if (val > 100) val = 100;
                    if (val < 0) val = 0;
                    setMcqWeight(val);
                    setFillWeight(100 - val);
                  }}
                />
              </div>
              <div className="form-group" style={{ flex: '1', minWidth: '160px', maxWidth: '220px', textAlign: 'left', marginBottom: '0' }}>
                <label style={{ fontSize: '0.85rem', fontWeight: 'bold', letterSpacing: '0.5px', textTransform: 'uppercase', display: 'block', marginBottom: '0.5rem', color: '#a0aec0' }}>Fill-in-Blanks Weight (%)</label>
                <input 
                  type="number" 
                  className="input" 
                  style={{ width: '100%', padding: '0.7rem', borderRadius: '6px', border: '1px solid #4a5568', backgroundColor: '#2d3748', color: '#fff' }}
                  value={fillWeight} 
                  onChange={(e) => {
                    let val = parseInt(e.target.value) || 0;
                    if (val > 100) val = 100;
                    if (val < 0) val = 0;
                    setFillWeight(val);
                    setMcqWeight(100 - val);
                  }}
                />
              </div>
            </div>
          )}

          <div className="text-center mt-3">
            <button
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={!file}
              style={{ padding: '0.85rem 2.5rem', fontSize: '1rem' }}
            >
              🚀 Upload & Generate Quiz
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default FacultyDashboard
