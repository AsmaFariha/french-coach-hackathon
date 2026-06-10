import { useEffect, useRef, useState } from 'react'
import { sendChat } from '../api'
import { speak } from '../tts'

export default function Chat({ lessonText }) {
  const [history, setHistory] = useState([])
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, sending])

  const handleSend = async () => {
    const text = message.trim()
    if (!text || sending) return
    setError('')
    const priorHistory = history
    setHistory((h) => [...h, { role: 'user', content: text }])
    setMessage('')
    setSending(true)
    try {
      const data = await sendChat(text, priorHistory, lessonText)
      setHistory((h) => [...h, { role: 'assistant', content: data.reply }])
    } catch (e) {
      setError(`Could not reach the coach: ${e.message}`)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="fc-card fc-chat">
      <p className="fc-muted">
        Ask anything about French — grammar, vocabulary, or your current lesson.
      </p>

      <div className="fc-chat-messages">
        {history.length === 0 && (
          <div className="fc-chat-msg fc-chat-msg-assistant fc-muted">
            Bonjour ! Ask me about a word, a grammar point, or anything from today's lesson.
          </div>
        )}
        {history.map((m, i) => (
          <div key={i} className={`fc-chat-msg fc-chat-msg-${m.role}`}>
            {m.content}
            {m.role === 'assistant' && (
              <button className="fc-chat-speak-btn" onClick={() => speak(m.content)}>🔊 Hear it</button>
            )}
          </div>
        ))}
        {sending && <div className="fc-chat-msg fc-chat-msg-assistant fc-muted">Thinking…</div>}
        <div ref={bottomRef} />
      </div>

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      <div className="fc-row">
        <input
          className="fc-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Comment dit-on… ?"
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        />
        <button className="fc-btn fc-btn-primary" onClick={handleSend} disabled={sending || !message.trim()}>
          {sending ? 'Sending…' : 'Send'}
        </button>
      </div>
    </div>
  )
}
