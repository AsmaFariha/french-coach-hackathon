import { useEffect, useState } from 'react'
import { getSummary } from '../api'

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// The summary is encouraging plain prose from the LLM (see prompts.py
// DAILY_SUMMARY_SYSTEM); render paragraphs and a little **bold** emphasis.
function formatSummary(text) {
  return escapeHtml(text)
    .split(/\n\s*\n/)
    .map((para) => `<p>${para.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')}</p>`)
    .join('')
}

export default function Summary() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getSummary()
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="fc-card fc-error">Could not load your summary: {error}</div>
  if (data === null) return <div className="fc-card fc-muted">Gathering your progress…</div>

  return (
    <div className="fc-summary">
      <div className="fc-card fc-summary-points">
        <div className="fc-summary-points-value">{data.total_points}</div>
        <div className="fc-summary-points-label">⭐ total points</div>
      </div>
      <div className="fc-card fc-summary-text" dangerouslySetInnerHTML={{ __html: formatSummary(data.summary) }} />
    </div>
  )
}
