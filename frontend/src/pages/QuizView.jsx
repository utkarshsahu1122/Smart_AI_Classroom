import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

function QuizView() {
  const [questions, setQuestions] = useState([])
  const [answers, setAnswers] = useState({})
  const [timeLeft, setTimeLeft] = useState(0)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [studentName, setStudentName] = useState('')
  const navigate = useNavigate()
  const timerRef = useRef(null)
  const sessionPollRef = useRef(null)
  const hasSubmittedRef = useRef(false)

  const studentId = sessionStorage.getItem('student_id')
  const sessionId = sessionStorage.getItem('session_id')

  const handleSubmit = useCallback(async (isAuto = false) => {
    if (hasSubmittedRef.current || submitting) return
    hasSubmittedRef.current = true
    setSubmitting(true)

    // Clear timers
    if (timerRef.current) clearInterval(timerRef.current)
    if (sessionPollRef.current) clearInterval(sessionPollRef.current)

    if (isAuto) {
      alert(isAuto === 'session_ended'
        ? 'The faculty has ended the session. Submitting your quiz...'
        : "Time's up! Submitting your quiz automatically..."
      )
    }

    try {
      const res = await fetch('/api/student/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: parseInt(studentId), answers }),
      })
      const data = await res.json()

      sessionStorage.setItem('quiz_score', data.score)
      sessionStorage.setItem('quiz_total', data.total)
      navigate('/student/result')
    } catch (err) {
      setError('Submission failed. Please try again.')
      hasSubmittedRef.current = false
      setSubmitting(false)
    }
  }, [answers, studentId, navigate, submitting])

  // Fetch quiz data
  useEffect(() => {
    if (!studentId) {
      navigate('/student/login')
      return
    }

    const fetchQuiz = async () => {
      try {
        const res = await fetch(`/api/student/quiz?student_id=${studentId}`)
        const data = await res.json()

        if (data.already_submitted) {
          sessionStorage.setItem('quiz_score', data.score)
          sessionStorage.setItem('quiz_total', data.total)
          navigate('/student/result')
          return
        }

        if (data.success) {
          setQuestions(data.questions)
          setStudentName(data.student_name)
          setTimeLeft(data.timer_minutes * 60)
        } else {
          setError(data.error || 'Failed to load quiz')
        }
      } catch (err) {
        setError('Server error loading quiz')
      } finally {
        setLoading(false)
      }
    }

    fetchQuiz()
  }, [studentId, navigate])

  // Timer countdown
  useEffect(() => {
    if (timeLeft <= 0 || loading) return

    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current)
          handleSubmit('time_up')
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timerRef.current)
  }, [loading, handleSubmit])

  // Poll for session end
  useEffect(() => {
    if (!sessionId || loading) return

    sessionPollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/student/check_session?session_id=${sessionId}`)
        const data = await res.json()
        if (!data.active) {
          clearInterval(sessionPollRef.current)
          handleSubmit('session_ended')
        }
      } catch (err) {}
    }, 5000)

    return () => clearInterval(sessionPollRef.current)
  }, [sessionId, loading, handleSubmit])

  const handleAnswerChange = (questionId, value) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s < 10 ? '0' : ''}${s}`
  }

  if (loading) {
    return (
      <div className="glass-card">
        <div className="spinner-overlay">
          <div className="spinner"></div>
          <p className="spinner-text">Loading your quiz...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return <div className="alert alert-error">⚠️ {error}</div>
  }

  const answeredCount = Object.keys(answers).filter((k) => answers[k]).length

  return (
    <div>
      {/* Header with Timer */}
      <div className="flex-between flex-wrap gap-md" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>Live Quiz</h2>
          <p className="text-secondary" style={{ fontSize: '0.85rem' }}>
            {studentName} &middot; {answeredCount}/{questions.length} answered
          </p>
        </div>
        <div className="timer-display">
          ⏱ {formatTime(timeLeft)}
        </div>
      </div>

      {/* Questions */}
      {questions.map((q, i) => (
        <div key={q.id} className="question-card">
          <div className="flex-between">
            <span className="question-number">Question {i + 1}</span>
            <span className={`question-type-badge ${q.type === 'mcq' ? 'mcq' : 'fill'}`}>
              {q.type === 'mcq' ? 'MCQ' : 'Fill in the Blank'}
            </span>
          </div>
          <p className="question-text">{q.text}</p>

          {q.type === 'mcq' ? (
            <div>
              {q.options.map((opt, j) => (
                <label key={j} className="option-label">
                  <input
                    type="radio"
                    name={`q_${q.id}`}
                    value={opt}
                    checked={answers[q.id] === opt}
                    onChange={() => handleAnswerChange(q.id, opt)}
                  />
                  <span>{opt}</span>
                </label>
              ))}
            </div>
          ) : (
            <input
              type="text"
              className="form-input"
              placeholder="Type your answer here..."
              value={answers[q.id] || ''}
              onChange={(e) => handleAnswerChange(q.id, e.target.value)}
            />
          )}
        </div>
      ))}

      {/* Submit Button */}
      <button
        className="btn btn-primary"
        onClick={() => handleSubmit(false)}
        disabled={submitting}
        style={{ width: '100%', padding: '1rem', fontSize: '1.05rem', marginTop: '1rem' }}
      >
        {submitting ? '⏳ Submitting...' : '📤 Submit Quiz Final Answers'}
      </button>
    </div>
  )
}

export default QuizView
