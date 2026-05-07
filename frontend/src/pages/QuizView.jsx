import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const STORAGE_KEY = 'active_quiz_state'

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

  // Proctoring state
  const [warningCount, setWarningCount] = useState(0)
  const [showWarning, setShowWarning] = useState(false)
  const [warningMessage, setWarningMessage] = useState('')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const warningCountRef = useRef(0)

  const studentId = sessionStorage.getItem('student_id')
  const sessionId = sessionStorage.getItem('session_id')
  const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

  // ─── Refs for stable callbacks ──────────────────
  const answersRef = useRef({})
  const questionsRef = useRef([])
  const timeLeftRef = useRef(0)
  const studentNameRef = useRef('')

  useEffect(() => { answersRef.current = answers }, [answers])
  useEffect(() => { questionsRef.current = questions }, [questions])
  useEffect(() => { timeLeftRef.current = timeLeft }, [timeLeft])
  useEffect(() => { studentNameRef.current = studentName }, [studentName])

  // ─── Save/Restore quiz state ────────────────────

  const saveQuizState = useCallback((q, a, t) => {
    const state = {
      questions: q || questionsRef.current,
      answers: a || answersRef.current,
      timeLeft: t !== undefined ? t : timeLeftRef.current,
      studentId,
      sessionId,
      studentName: studentNameRef.current,
      savedAt: Date.now(),
    }
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }, [studentId, sessionId])

  const clearQuizState = () => {
    sessionStorage.removeItem(STORAGE_KEY)
  }

  // ─── Submit handler ─────────────────────────────

  const handleSubmit = useCallback(async (reason = 'manual') => {
    if (hasSubmittedRef.current || submitting) return
    hasSubmittedRef.current = true
    setSubmitting(true)

    if (timerRef.current) clearInterval(timerRef.current)
    if (sessionPollRef.current) clearInterval(sessionPollRef.current)

    // Exit fullscreen
    if (document.fullscreenElement) {
      try { await document.exitFullscreen() } catch {}
    }

    if (reason === 'session_ended') {
      alert('The faculty has ended the session. Submitting your quiz...')
    } else if (reason === 'time_up') {
      alert("Time's up! Submitting your quiz automatically...")
    } else if (reason === 'proctoring') {
      alert('⚠️ Maximum warnings exceeded. Your quiz is being auto-submitted due to suspected unfair means.')
    }

    try {
      const res = await fetch(`${API_BASE}/api/student/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          answers: answersRef.current,
          reason,
        }),
      })
      const data = await res.json()

      clearQuizState()
      sessionStorage.setItem('quiz_score', data.score)
      sessionStorage.setItem('quiz_total', data.total)
      navigate('/student/result')
    } catch (err) {
      setError('Backend not connected. Please try again later.')
      hasSubmittedRef.current = false
      setSubmitting(false)
    }
  }, [studentId, navigate, submitting, API_BASE])

  // ─── Proctoring: record warning ─────────────────

  const recordWarning = useCallback(async (reason) => {
    if (hasSubmittedRef.current) return

    const newCount = warningCountRef.current + 1
    warningCountRef.current = newCount
    setWarningCount(newCount)

    // Show warning modal
    if (newCount === 1) {
      setWarningMessage(`⚠️ Warning 1/2: ${reason}. One more violation and your quiz will be auto-submitted!`)
      setShowWarning(true)
    }

    // Report to backend
    try {
      const res = await fetch(`${API_BASE}/api/student/proctor/warn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, reason }),
      })
      const data = await res.json()

      if (data.auto_submit || newCount >= 2) {
        setShowWarning(false)
        handleSubmit('proctoring')
      }
    } catch (err) {
      console.error('Proctoring report failed (Backend not connected).', err)
    }
  }, [studentId, handleSubmit, API_BASE])

  // ─── Proctoring: setup event listeners ──────────

  useEffect(() => {
    if (loading || !questions.length) return

    // Fullscreen on quiz start
    const enterFullscreen = async () => {
      try {
        await document.documentElement.requestFullscreen()
        setIsFullscreen(true)
      } catch {}
    }
    enterFullscreen()

    // Tab switch / blur detection
    const handleVisibility = () => {
      if (document.hidden && !hasSubmittedRef.current) {
        recordWarning('Tab switch or window minimized detected')
      }
    }
    const handleBlur = () => {
      if (!hasSubmittedRef.current) {
        recordWarning('Window focus lost — possible tab switch')
      }
    }

    // Fullscreen exit detection
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement && !hasSubmittedRef.current) {
        setIsFullscreen(false)
        recordWarning('Fullscreen mode exited')
      } else {
        setIsFullscreen(true)
      }
    }

    // Copy / right-click / devtools prevention
    const handleCopy = (e) => { e.preventDefault() }
    const handleContextMenu = (e) => { e.preventDefault() }
    const handleKeydown = (e) => {
      // Prevent common devtools shortcuts
      if (e.key === 'F12') { e.preventDefault(); return }
      if (e.ctrlKey && e.shiftKey && ['I', 'J', 'C'].includes(e.key)) { e.preventDefault(); return }
      if (e.ctrlKey && e.key === 'u') { e.preventDefault(); return }
    }
    const handleSelectStart = (e) => { e.preventDefault() }

    document.addEventListener('visibilitychange', handleVisibility)
    window.addEventListener('blur', handleBlur)
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('copy', handleCopy)
    document.addEventListener('contextmenu', handleContextMenu)
    document.addEventListener('keydown', handleKeydown)
    document.addEventListener('selectstart', handleSelectStart)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibility)
      window.removeEventListener('blur', handleBlur)
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('copy', handleCopy)
      document.removeEventListener('contextmenu', handleContextMenu)
      document.removeEventListener('keydown', handleKeydown)
      document.removeEventListener('selectstart', handleSelectStart)
    }
  }, [loading, questions.length, recordWarning])

  // ─── Fetch quiz / restore state ─────────────────

  useEffect(() => {
    if (!studentId) {
      navigate('/student/login')
      return
    }

    // Try to restore saved state first
    const saved = sessionStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const state = JSON.parse(saved)
        // Only restore if it's for the same student and not too old (< 15 min)
        if (state.studentId === studentId && (Date.now() - state.savedAt) < 15 * 60 * 1000) {
          setQuestions(state.questions)
          setAnswers(state.answers)
          setStudentName(state.studentName)
          // Recalculate time: subtract elapsed seconds since save
          const elapsed = Math.floor((Date.now() - state.savedAt) / 1000)
          const remaining = Math.max(0, state.timeLeft - elapsed)
          setTimeLeft(remaining)
          setLoading(false)
          console.log('[Quiz] Restored saved state, time remaining:', remaining)
          return
        }
      } catch {}
    }

    // Fresh fetch from backend
    const fetchQuiz = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/student/quiz?student_id=${studentId}`)
        const data = await res.json()

        if (data.already_submitted) {
          clearQuizState()
          sessionStorage.setItem('quiz_score', data.score)
          sessionStorage.setItem('quiz_total', data.total)
          navigate('/student/result')
          return
        }

        if (data.success) {
          setQuestions(data.questions)
          setStudentName(data.student_name)
          setTimeLeft(data.timer_minutes * 60)
          saveQuizState(data.questions, {}, data.timer_minutes * 60)
        } else {
          setError(data.error || 'Failed to load quiz')
        }
      } catch (err) {
        setError('Backend not connected. Please try again later.')
      } finally {
        setLoading(false)
      }
    }

    fetchQuiz()
  }, [studentId, navigate, API_BASE, saveQuizState])

  // ─── Timer countdown ────────────────────────────

  useEffect(() => {
    if (timeLeft <= 0 || loading) return

    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0))
    }, 1000)

    return () => clearInterval(timerRef.current)
  }, [loading])

  // Timer side effects
  useEffect(() => {
    if (loading) return

    if (timeLeft <= 0 && !hasSubmittedRef.current) {
      handleSubmit('time_up')
    } else if (timeLeft > 0 && timeLeft % 5 === 0) {
      saveQuizState(undefined, undefined, timeLeft)
    }
  }, [timeLeft, loading, handleSubmit, saveQuizState])

  // ─── Poll for session end ───────────────────────

  useEffect(() => {
    if (!sessionId || loading) return

    sessionPollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/student/check_session?session_id=${sessionId}`)
        const data = await res.json()
        if (!data.active) {
          clearInterval(sessionPollRef.current)
          handleSubmit('session_ended')
        }
      } catch (err) {}
    }, 5000)

    return () => clearInterval(sessionPollRef.current)
  }, [sessionId, loading, handleSubmit, API_BASE])

  // ─── Answer change handler ──────────────────────

  const handleAnswerChange = (questionId, value) => {
    const updated = { ...answers, [questionId]: value }
    setAnswers(updated)
    saveQuizState(undefined, updated, undefined)
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
      {/* Proctoring Warning Modal */}
      {showWarning && (
        <div className="proctor-overlay">
          <div className="proctor-modal">
            <div className="proctor-icon">⚠️</div>
            <h3>Proctoring Violation</h3>
            <p>{warningMessage}</p>
            <button
              className="btn btn-danger"
              onClick={() => {
                setShowWarning(false)
                // Re-enter fullscreen
                try { document.documentElement.requestFullscreen() } catch {}
              }}
            >
              I Understand — Resume Quiz
            </button>
          </div>
        </div>
      )}

      {/* Warning indicator */}
      {warningCount > 0 && (
        <div className="proctor-badge">
          ⚠️ Warnings: {warningCount}/2
        </div>
      )}

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
        onClick={() => handleSubmit('manual')}
        disabled={submitting}
        style={{ width: '100%', padding: '1rem', fontSize: '1.05rem', marginTop: '1rem' }}
      >
        {submitting ? '⏳ Submitting...' : '📤 Submit Quiz Final Answers'}
      </button>
    </div>
  )
}

export default QuizView
