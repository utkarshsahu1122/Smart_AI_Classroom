function ChatHistorySidebar({ sessions, activeSessionId, onSelect, onNewChat }) {
  return (
    <div className="chat-sidebar">
      <div className="sidebar-header">
        <h3>Chat History</h3>
        <button className="btn btn-primary btn-sm" onClick={onNewChat}>
          + New Chat
        </button>
      </div>

      <div className="sidebar-list">
        {sessions.length === 0 ? (
          <p className="text-muted" style={{ padding: '1rem', fontSize: '0.82rem' }}>
            No conversations yet. Upload a PDF and start asking questions!
          </p>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              className={`sidebar-item ${s.id === activeSessionId ? 'active' : ''}`}
              onClick={() => onSelect(s.id)}
            >
              <div className="sidebar-item-title">{s.title}</div>
              <div className="sidebar-item-meta">
                <span>📄 {s.document || 'No PDF'}</span>
                <span>{s.message_count} msgs</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ChatHistorySidebar
