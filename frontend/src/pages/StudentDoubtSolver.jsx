import { useState, useEffect, useRef } from 'react'
import ChatBubble from '../components/ChatBubble'
import ChatHistorySidebar from '../components/ChatHistorySidebar'

// ─── Token helpers ────────────────────────────────
function getToken() { return localStorage.getItem('doubt_token') }
function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`,
  }
}
async function authFetch(url, opts = {}) {
  opts.headers = { ...opts.headers, 'Authorization': `Bearer ${getToken()}` }
  const res = await fetch(url, opts)
  if (res.status === 401) {
    localStorage.clear()
    window.location.reload()
  }
  return res
}

function StudentDoubtSolver() {
  const messagesEndRef = useRef(null)

  // Auth state
  const [loggedIn, setLoggedIn] = useState(!!getToken())
  const [studentId, setStudentId] = useState(localStorage.getItem('doubt_student_id'))
  const [studentName, setStudentName] = useState(localStorage.getItem('doubt_student_name') || '')
  const [authMode, setAuthMode] = useState('login') // 'login' or 'register'
  const [authForm, setAuthForm] = useState({ name: '', roll_no: '', password: '' })
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)

  // Documents
  const [documents, setDocuments] = useState([])
  const [selectedDocId, setSelectedDocId] = useState(null)
  const [uploading, setUploading] = useState(false)

  // Chat state
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [query, setQuery] = useState('')
  const [sending, setSending] = useState(false)
  const [chatTitle, setChatTitle] = useState('')

  // Sidebar toggle
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (loggedIn && studentId) {
      fetchDocuments()
      fetchSessions()
    }
  }, [loggedIn])

  // ─── Auth ───────────────────────────────────────

  const handleAuth = async (e) => {
    e.preventDefault()
    setAuthError('')
    setAuthLoading(true)
    const endpoint = authMode === 'register' ? '/api/doubt/register' : '/api/doubt/login'

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(authForm),
      })
      const data = await res.json()
      if (data.success) {
        localStorage.setItem('doubt_token', data.token)
        localStorage.setItem('doubt_student_id', data.student_id)
        localStorage.setItem('doubt_student_name', data.name)
        setStudentId(data.student_id)
        setStudentName(data.name)
        setLoggedIn(true)
        setDocuments(data.documents || [])
      } else {
        setAuthError(data.error)
      }
    } catch {
      setAuthError('Server error. Make sure the backend is running.')
    }
    setAuthLoading(false)
  }

  const handleLogout = () => {
    localStorage.removeItem('doubt_token')
    localStorage.removeItem('doubt_student_id')
    localStorage.removeItem('doubt_student_name')
    setLoggedIn(false)
    setStudentId(null)
    setMessages([])
    setSessions([])
    setActiveSessionId(null)
  }

  // ─── API Calls ──────────────────────────────────

  const fetchDocuments = async () => {
    try {
      const res = await authFetch('/api/doubt/documents')
      const data = await res.json()
      if (data.success) setDocuments(data.documents)
    } catch {}
  }

  const fetchSessions = async () => {
    try {
      const res = await authFetch('/api/doubt/chat/history')
      const data = await res.json()
      if (data.success) setSessions(data.sessions)
    } catch {}
  }

  const handleUploadPdf = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    const formData = new FormData()
    formData.append('pdf_file', file)

    try {
      const res = await authFetch('/api/doubt/upload-pdf', { method: 'POST', body: formData })
      const data = await res.json()
      if (data.success) {
        setSelectedDocId(data.document_id)
        fetchDocuments()
      }
    } catch {}
    setUploading(false)
    e.target.value = ''
  }

  const handleNewChat = async () => {
    if (!selectedDocId) {
      alert('Please select or upload a PDF first')
      return
    }
    try {
      const res = await authFetch('/api/doubt/chat/create', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ document_id: selectedDocId }),
      })
      const data = await res.json()
      if (data.success) {
        setActiveSessionId(data.session_id)
        setMessages([])
        setChatTitle('New Chat')
        fetchSessions()
        setSidebarOpen(false)
      }
    } catch {}
  }

  const handleSelectSession = async (sessionId) => {
    setActiveSessionId(sessionId)
    setSidebarOpen(false)
    try {
      const res = await authFetch(`/api/doubt/chat/${sessionId}/messages`)
      const data = await res.json()
      if (data.success) {
        setMessages(data.messages)
        setChatTitle(data.title)
      }
    } catch {}
  }

  const handleSend = async (e) => {
    e.preventDefault()
    if (!query.trim() || !activeSessionId || sending) return

    const userMsg = { role: 'user', content: query, sources: [] }
    setMessages((prev) => [...prev, userMsg])
    const q = query.trim()
    setQuery('')
    setSending(true)

    try {
      const res = await authFetch('/api/doubt/chat/send', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ session_id: activeSessionId, query: q }),
      })
      const data = await res.json()
      if (data.success) {
        const aiMsg = { role: 'assistant', content: data.answer, sources: data.sources || [] }
        setMessages((prev) => [...prev, aiMsg])
        fetchSessions()
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `⚠️ ${data.error}`, sources: [] },
        ])
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '⚠️ Server error. Please try again.', sources: [] },
      ])
    }
    setSending(false)
  }

  const handleDownload = async () => {
    if (!activeSessionId) return
    try {
      const res = await authFetch(`/api/doubt/chat/${activeSessionId}/download`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `doubt_summary_${activeSessionId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  // ─── Login / Register Screen ────────────────────

  if (!loggedIn) {
    return (
      <div style={{ maxWidth: 440, margin: '0 auto' }}>
        <div className="page-header">
          <h1>Doubt Solver</h1>
          <p>{authMode === 'login' ? 'Login to continue your study sessions' : 'Create a new account to get started'}</p>
        </div>
        {authError && <div className="alert alert-error">⚠️ {authError}</div>}
        <div className="glass-card">
          <form onSubmit={handleAuth}>
            {authMode === 'register' && (
              <div className="form-group">
                <label>Full Name</label>
                <input
                  className="form-input"
                  placeholder="Enter your name"
                  value={authForm.name}
                  onChange={(e) => setAuthForm({ ...authForm, name: e.target.value })}
                  required
                  autoFocus
                />
              </div>
            )}
            <div className="form-group">
              <label>Roll Number</label>
              <input
                className="form-input"
                placeholder="e.g. 112215191"
                value={authForm.roll_no}
                onChange={(e) => setAuthForm({ ...authForm, roll_no: e.target.value })}
                required
                autoFocus={authMode === 'login'}
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                className="form-input"
                type="password"
                placeholder={authMode === 'register' ? 'Create a password (min 4 chars)' : 'Enter your password'}
                value={authForm.password}
                onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                required
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={authLoading} style={{ width: '100%' }}>
              {authLoading ? '⏳ Please wait...' : authMode === 'login' ? '🔐 Login' : '🚀 Register & Start'}
            </button>
          </form>
          <p className="text-center mt-2" style={{ fontSize: '0.82rem' }}>
            {authMode === 'login' ? (
              <>Don't have an account? <a href="#" onClick={(e) => { e.preventDefault(); setAuthMode('register'); setAuthError('') }}>Register here</a></>
            ) : (
              <>Already registered? <a href="#" onClick={(e) => { e.preventDefault(); setAuthMode('login'); setAuthError('') }}>Login here</a></>
            )}
          </p>
        </div>
      </div>
    )
  }

  // ─── Main Chat Interface ────────────────────────

  return (
    <div className="doubt-solver-layout">
      {/* Sidebar */}
      <div className={`doubt-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-user-info">
          <span>👤 {studentName}</span>
          <button className="btn btn-outline btn-sm" onClick={handleLogout}>Logout</button>
        </div>

        {/* PDF selector */}
        <div className="sidebar-section">
          <label className="sidebar-label">Active PDF</label>
          <select
            className="form-input"
            value={selectedDocId || ''}
            onChange={(e) => setSelectedDocId(parseInt(e.target.value))}
            style={{ fontSize: '0.8rem' }}
          >
            <option value="">— Select a PDF —</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>{d.filename}</option>
            ))}
          </select>
          <label className="upload-btn mt-1">
            {uploading ? '⏳ Processing...' : '📤 Upload New PDF'}
            <input type="file" accept=".pdf" onChange={handleUploadPdf} disabled={uploading} style={{ display: 'none' }} />
          </label>
        </div>

        <ChatHistorySidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelect={handleSelectSession}
          onNewChat={handleNewChat}
        />
      </div>

      {/* Mobile sidebar toggle */}
      <button className="sidebar-toggle-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
        {sidebarOpen ? '✕' : '☰'}
      </button>

      {/* Chat area */}
      <div className="doubt-chat-area">
        {!activeSessionId ? (
          <div className="chat-empty-state">
            <div className="empty-icon">🤖</div>
            <h2>AI Doubt Solver</h2>
            <p>Upload a PDF, select it, then click <strong>"+ New Chat"</strong> to start asking questions</p>
            {selectedDocId && (
              <button className="btn btn-primary mt-2" onClick={handleNewChat}>
                + Start New Chat
              </button>
            )}
          </div>
        ) : (
          <>
            {/* Chat header */}
            <div className="chat-header">
              <div>
                <h3 className="chat-title">{chatTitle}</h3>
              </div>
              <button className="btn btn-outline btn-sm" onClick={handleDownload}>
                📥 Download PDF
              </button>
            </div>

            {/* Messages */}
            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="chat-empty-state" style={{ padding: '3rem 1rem' }}>
                  <p className="text-muted">Ask your first question about the uploaded PDF!</p>
                </div>
              )}
              {messages.map((msg, i) => (
                <ChatBubble
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                  timestamp={msg.created_at}
                />
              ))}
              {sending && (
                <div className="chat-bubble-wrapper assistant">
                  <div className="chat-bubble bubble-assistant">
                    <div className="typing-indicator">
                      <span></span><span></span><span></span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form className="chat-input-bar" onSubmit={handleSend}>
              <input
                type="text"
                className="chat-input"
                placeholder="Ask a question about your material..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={sending}
                autoFocus
              />
              <button type="submit" className="btn btn-primary chat-send-btn" disabled={sending || !query.trim()}>
                {sending ? '⏳' : '➤'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

export default StudentDoubtSolver
