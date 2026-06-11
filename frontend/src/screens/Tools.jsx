import { useState } from 'react'
import { annotate, renderAnnotations, wordCard } from '../api'
import { speak } from '../tts'
import WordCard from '../components/WordCard'
import { GenderChecker, TranslatorPanel } from '../components/QuickTools'

const SUBTABS = [
  { id: 'gender', label: '🔤 Gender Checker' },
  { id: 'translate', label: '🔁 Translator' },
  { id: 'text', label: '📝 Text Checker' },
]

// ── Text Checker (paste any text, gender colors + word card) ────────────────

function TextChecker() {
  const [text, setText] = useState('')
  const [ann, setAnn] = useState({ tokens: [], meanings: {} })
  const [html, setHtml] = useState('')
  const [colorsOn, setColorsOn] = useState(true)
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [wordCardData, setWordCardData] = useState(null)
  const [wordCardLoading, setWordCardLoading] = useState(false)

  const handleCheck = async () => {
    if (!text.trim()) { setStatus('Paste some French text first.'); return }
    setLoading(true)
    setStatus('')
    try {
      const data = await annotate(text, colorsOn)
      setAnn({ tokens: data.tokens, meanings: data.meanings })
      setHtml(data.html)
      setWordCardData(null)
    } catch (e) {
      setStatus(`⚠ Could not check this text: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleColors = async (checked) => {
    setColorsOn(checked)
    if (!html) return
    try {
      const r = await renderAnnotations(ann, checked)
      setHtml(r.html)
    } catch {
      /* ignore */
    }
  }

  const handleContainerClick = async (e) => {
    const tok = e.target.closest('[data-token]')
    if (!tok) return
    const tokenInfo = {
      text: tok.dataset.text,
      gender: tok.dataset.gender || '',
      pos: tok.dataset.pos || '',
      lemma: tok.dataset.lemma || tok.dataset.text,
    }
    speak(tokenInfo.text)
    setWordCardLoading(true)
    setWordCardData({ ...tokenInfo, meaning: '', grammar: '' })
    try {
      const data = await wordCard(tokenInfo, ann.meanings)
      setAnn((prev) => ({ ...prev, meanings: data.meanings }))
      setWordCardData(data)
    } catch (err) {
      setWordCardData({ ...tokenInfo, meaning: `⚠ ${err.message}`, grammar: '' })
    } finally {
      setWordCardLoading(false)
    }
  }

  return (
    <div className="fc-notebook">
      <div className="fc-notebook-main">
        <p className="fc-muted">
          Paste any French text — a menu, a sign, an email — to see gender at a glance and click any
          word for its meaning, grammar, and pronunciation. Nothing here is saved to your notebook.
        </p>

        <textarea
          className="fc-textarea"
          rows={6}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste French text here…"
        />

        <div className="fc-row">
          <button className="fc-btn fc-btn-primary" onClick={handleCheck} disabled={loading}>
            {loading ? 'Checking…' : '🔍 Check text'}
          </button>
          <label className="fc-checkbox">
            <input type="checkbox" checked={colorsOn} onChange={(e) => handleToggleColors(e.target.checked)} />
            Gender colors
          </label>
        </div>

        {status && <div className="fc-status">{status}</div>}

        {html && (
          <div className="fc-annotated" dangerouslySetInnerHTML={{ __html: html }} onClick={handleContainerClick} />
        )}
      </div>

      <div className="fc-notebook-side">
        <h3>🔤 Word card</h3>
        <div className="fc-card">
          <WordCard data={wordCardData} loading={wordCardLoading} />
        </div>
      </div>
    </div>
  )
}

// ── Screen ─────────────────────────────────────────────────────────────────

export default function Tools({ lessonText }) {
  const [view, setView] = useState('gender')

  return (
    <div>
      <nav className="fc-subtabs">
        {SUBTABS.map((t) => (
          <button
            key={t.id}
            className={`fc-subtab${view === t.id ? ' fc-subtab-active' : ''}`}
            onClick={() => setView(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {view === 'gender' && <GenderChecker />}
      {view === 'translate' && <TranslatorPanel lessonText={lessonText} />}
      {view === 'text' && <TextChecker />}
    </div>
  )
}
