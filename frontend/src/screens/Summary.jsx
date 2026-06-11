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

const STAT_LABELS = [
  { key: 'pages_today', icon: '📓', label: 'lessons saved today' },
  { key: 'exercises_today', icon: '🏋️', label: 'exercises completed today' },
  { key: 'dialogue_turns', icon: '💬', label: 'dialogue turns today' },
  { key: 'words_clicked', icon: '🔤', label: 'words explored today' },
]

export default function Summary() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getSummary()
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="fc-card fc-error">Could not load your summary: {error}</div>
  if (data === null) return <div className="fc-empty"><span className="fc-spinner" />Gathering your progress…</div>

  const stats = data.daily_stats || {}
  const concepts = data.concepts || {}
  const covered = concepts.covered || []
  const total = concepts.total_count || 0
  const coveredCount = concepts.covered_count || 0
  const pct = total > 0 ? Math.round((coveredCount / total) * 100) : 0

  return (
    <div className="fc-summary">
      <div className="fc-card fc-summary-points">
        <div className="fc-summary-points-value">{data.total_points}</div>
        <div className="fc-summary-points-label">⭐ total points</div>
      </div>

      <div className="fc-card fc-summary-text" dangerouslySetInnerHTML={{ __html: formatSummary(data.summary) }} />

      <div className="fc-summary-stats">
        {STAT_LABELS.map((s) => (
          <div className="fc-card fc-stat-card" key={s.key}>
            <div className="fc-stat-value">{stats[s.key] ?? 0}</div>
            <div className="fc-stat-label">{s.icon} {s.label}</div>
          </div>
        ))}
      </div>

      {total > 0 && (
        <div className="fc-card fc-summary-progress">
          <div className="fc-progress-header">
            <span>A1–A2 concepts covered</span>
            <span>{coveredCount} / {total}</span>
          </div>
          <div className="fc-progress-bar">
            <div className="fc-progress-fill" style={{ width: `${pct}%` }} />
          </div>
          {covered.length > 0 && (
            <div className="fc-summary-pills">
              {covered.slice(-6).map((name) => (
                <span className="fc-pill" key={name}>✓ {name}</span>
              ))}
            </div>
          )}
          {concepts.next && (
            <div className="fc-summary-next">🎯 Ready to practice next: <strong>{concepts.next}</strong></div>
          )}
        </div>
      )}
    </div>
  )
}
