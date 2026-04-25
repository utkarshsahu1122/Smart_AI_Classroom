import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'

function QuizResult() {
  const navigate = useNavigate()
  const studentName = sessionStorage.getItem('student_name')
  const score = sessionStorage.getItem('quiz_score')
  const total = sessionStorage.getItem('quiz_total')

  useEffect(() => {
    if (!score || !total) {
      navigate('/student/login')
    }
  }, [score, total, navigate])

  if (!score || !total) return null

  const percentage = Math.round((parseInt(score) / parseInt(total)) * 100)
  const isPassed = percentage >= 50

  // Clear student data so they can't go back
  const handleClose = () => {
    sessionStorage.clear()
    navigate('/student/login')
  }

  return (
    <div style={{ maxWidth: 520, margin: '0 auto' }}>
      <div className="glass-card">
        <div className="score-display">
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.25rem' }}>
            Quiz Submitted! 🎉
          </h2>
          <p className="text-secondary">Thank you, <strong style={{ color: 'var(--text-primary)' }}>{studentName}</strong></p>

          <div className="score-circle">
            <span className="score-number">{score}</span>
            <span className="score-total">out of {total}</span>
          </div>

          <p style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '1rem' }}>
            {percentage}% —{' '}
            <span style={{ color: isPassed ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {isPassed ? 'Well Done!' : 'Keep Practicing'}
            </span>
          </p>

          <p className="text-muted mt-2" style={{ fontSize: '0.82rem' }}>
            Your results have been recorded. You may safely close this window.
          </p>

          <button className="btn btn-outline mt-3" onClick={handleClose}>
            ← Return to Login
          </button>
        </div>
      </div>
    </div>
  )
}

export default QuizResult
