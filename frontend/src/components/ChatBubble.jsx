function ChatBubble({ role, content, sources, timestamp }) {
  const isUser = role === 'user'

  return (
    <div className={`chat-bubble-wrapper ${isUser ? 'user' : 'assistant'}`}>
      <div className={`chat-bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
        <div className="bubble-header">
          <span className="bubble-role">{isUser ? '📝 You' : '🤖 AI Tutor'}</span>
          {timestamp && <span className="bubble-time">{timestamp}</span>}
        </div>
        <div className="bubble-content">{content}</div>

        {!isUser && sources && sources.length > 0 && (
          <div className="bubble-sources">
            <details>
              <summary className="sources-toggle">📚 Sources ({sources.length})</summary>
              {sources.map((src, i) => (
                <div key={i} className="source-snippet">
                  <span className="source-label">Chunk {i + 1}:</span>
                  <p>{src}</p>
                </div>
              ))}
            </details>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatBubble
