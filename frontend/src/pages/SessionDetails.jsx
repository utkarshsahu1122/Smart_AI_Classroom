import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'

function SessionDetails() {
  const { sessionCode } = useParams()
  const [session, setSession] = useState(null)
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [ending, setEnding] = useState(false)

  const fetchSession = async () => {
    try {
      const res = await fetch(`/api/faculty/session/${sessionCode}`)
      const data = await res.json()
      if (data.success) {
        setSession(data.session)
        setStudents(data.students)
      }
    } catch (err) {
      console.error('Failed to fetch session:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSession()
    // Auto-refresh every 8 seconds while session is active
    const interval = setInterval(fetchSession, 8000)
    return () => clearInterval(interval)
  }, [sessionCode])

  const handleEndSession = async () => {
    if (!confirm('Are you sure? All pending students will be auto-submitted.')) return
    setEnding(true)
    try {
      const res = await fetch(`/api/faculty/session/${sessionCode}/end`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        setMessage(`Session ended! ${data.auto_submitted} pending student(s) were auto-submitted.`)
        fetchSession()
      }
    } catch (err) {
      setMessage('Error ending session')
    } finally {
      setEnding(false)
    }
  }

  if (loading) {
    return (
      <div className="glass-card">
        <div className="spinner-overlay">
          <div className="spinner"></div>
          <p className="spinner-text">Loading session details...</p>
        </div>
      </div>
    )
  }

  if (!session) {
    return <div className="alert alert-error">Session not found</div>
  }

  return (
    <div>
      <div className="page-header">
        <h1>Quiz Session</h1>
        <div className="flex-center gap-md mt-1">
          {session.is_active ? (
            <span className="badge badge-live">● Live</span>
          ) : (
            <span className="badge badge-ended">● Ended</span>
          )}
          <span className="text-secondary" style={{ fontSize: '0.9rem' }}>
            Code: <strong style={{ color: 'var(--accent-cyan)', fontSize: '1.1rem' }}>{session.session_code}</strong>
          </span>
        </div>
      </div>

      {message && <div className="alert alert-success">✅ {message}</div>}

      {/* QR Code + Info */}
      <div className="glass-card text-center">
        <p className="text-secondary" style={{ marginBottom: '1rem' }}>Ask students to scan this QR code to join:</p>

        {session.qr_url && (
          <div className="qr-container">
            <img src={session.qr_url} alt="Session QR Code" />
          </div>
        )}

        <div className="flex-center gap-lg mt-3 flex-wrap" style={{ fontSize: '0.85rem' }}>
          <span className="text-secondary">⏱ Timer: <strong>{session.timer_minutes} min</strong></span>
          <span className="text-secondary">📝 Pool: <strong>{session.questions_count} questions</strong></span>
          <span className="text-secondary">📅 {session.created_at}</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex-center gap-md mt-3 flex-wrap">
        <Link to="/faculty" className="btn btn-outline">← New Session</Link>

        {session.is_active && (
          <button
            className="btn btn-danger"
            onClick={handleEndSession}
            disabled={ending}
          >
            {ending ? '⏳ Ending...' : '⛔ End Session'}
          </button>
        )}

        <a
          href={`/api/faculty/session/${sessionCode}/report`}
          className="btn btn-success"
          download
        >
          📊 Download Excel Report
        </a>
      </div>

      {/* Student Table */}
      <div className="glass-card mt-4">
        <div className="flex-between">
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Students ({students.length})</h3>
          {session.is_active && (
            <span className="text-muted" style={{ fontSize: '0.75rem' }}>Auto-refreshing every 8s</span>
          )}
        </div>

        {students.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Roll No</th>
                <th>Name</th>
                <th>Status</th>
                <th>Score</th>
                <th>Integrity</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s, i) => (
                <tr key={s.id}>
                  <td>{i + 1}</td>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.roll_no}</td>
                  <td>{s.name}</td>
                  <td>
                    {s.submitted ? (
                      <span className="badge badge-submitted">✅ Submitted</span>
                    ) : s.is_logged_in ? (
                      <span className="badge badge-active">⏳ Taking Quiz</span>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    {s.submitted ? `${s.score}/${s.total}` : '—'}
                  </td>
                  <td>
                    {s.unfair_means ? (
                      <span className="badge badge-danger" title={`${s.warning_count} warning(s)`}>🚫 UNFAIR</span>
                    ) : s.warning_count > 0 ? (
                      <span className="text-muted" style={{ fontSize: '0.75rem' }}>⚠️ {s.warning_count} warn</span>
                    ) : (
                      <span style={{ color: 'var(--accent-green)', fontSize: '0.8rem' }}>✓ Fair</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-muted text-center mt-3">No students have joined yet.</p>
        )}
      </div>
    </div>
  )
}

export default SessionDetails
