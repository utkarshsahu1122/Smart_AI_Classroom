import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { API_BASE } from '../config'

function StudentLogin() {
  const [searchParams] = useSearchParams()
  const [name, setName] = useState('')
  const [rollNo, setRollNo] = useState('')
  const [sessionCode, setSessionCode] = useState(searchParams.get('session') || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  // If a quiz is already active, redirect straight to it
  useEffect(() => {
    const activeQuiz = sessionStorage.getItem('active_quiz_state')
    const studentId = sessionStorage.getItem('student_id')
    if (activeQuiz && studentId) {
      navigate('/student/quiz')
    }
  }, [navigate])

  const handleLogin = async (e) => {
    e.preventDefault()
    if (!name.trim() || !rollNo.trim() || !sessionCode.trim()) {
      setError('All fields are required')
      return
    }

    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${API_BASE}/api/student/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          roll_no: rollNo.trim(),
          session_code: sessionCode.trim().toUpperCase(),
        }),
      })
      const data = await res.json()

      if (data.success) {
        // Store credentials in sessionStorage for quiz page
        sessionStorage.setItem('student_id', data.student_id)
        sessionStorage.setItem('session_id', data.session_id)
        sessionStorage.setItem('student_name', data.student_name)
        sessionStorage.setItem('timer_minutes', data.timer_minutes)
        navigate('/student/quiz')
      } else {
        setError(data.error || 'Login failed')
      }
    } catch (err) {
      setError('Backend not connected. Please try again later.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 480, margin: '0 auto' }}>
      <div className="page-header">
        <h1>Join Quiz</h1>
        <p>Enter your details and session code to start</p>
      </div>

      {error && <div className="alert alert-error">⚠️ {error}</div>}

      <div className="glass-card">
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <input
              id="name"
              type="text"
              className="form-input"
              placeholder="Enter your full name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="roll_no">Roll Number</label>
            <input
              id="roll_no"
              type="text"
              className="form-input"
              placeholder="e.g. 112215191"
              value={rollNo}
              onChange={(e) => setRollNo(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="session_code">Session Code</label>
            <input
              id="session_code"
              type="text"
              className="form-input"
              placeholder="e.g. 822A2C83"
              value={sessionCode}
              onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
              required
              style={{ letterSpacing: '2px', fontWeight: 700 }}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', padding: '0.85rem', fontSize: '1rem', marginTop: '0.5rem' }}
          >
            {loading ? '⏳ Joining...' : '🚀 Start My Quiz'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default StudentLogin
