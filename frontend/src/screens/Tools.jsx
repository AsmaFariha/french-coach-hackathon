import { useState } from 'react'
import { annotate, renderAnnotations, wordCard, genderCheck, translateText } from '../api'
import { speak } from '../tts'
import WordCard from '../components/WordCard'

const SUBTABS = [
  { id: 'gender', label: '🔤 Gender Checker' },
  { id: 'translate', label: '🔁 Translator' },
  { id: 'text', label: '📝 Text Checker' },
]

// ── Gender Checker ───────────────────────────────────────────────────────────

const GENDER_COLORS = { Masc: '#4A90D9', Fem: '#D96B8A' }
const GENDER_LABELS = { Masc: 'Masculine ♂', Fem: 'Feminine ♀' }

function GenderChecker() {
  const [word, setWord] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleCheck = async () => {
    const w = word.trim()
    if (!w) return
    setLoading(true)
    setError('')
    try {
      const result = await genderCheck(w)
      setData(result)
    } catch (e) {
      setError(`Could not check this word: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const color = data?.gender ? GENDER_COLORS[data.gender] : 'var(--fc-ink)'

  return (
    <div>
      <p className="fc-muted">
        Type a French noun to see its gender, articles (le/la, un/une), an example sentence, and a tip for remembering it.
      </p>

      <div className="fc-row">
        <input
          className="fc-input"
          value={word}
          onChange={(e) => setWord(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
          placeholder="e.g. pomme, restaurant, voiture…"
        />
        <button className="fc-btn fc-btn-primary" onClick={handleCheck} disabled={loading || !word.trim()}>
          {loading ? 'Checking…' : '🔍 Check'}
        </button>
      </div>

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {data && (
        <div className="fc-card fc-gender-result">
          <div className="fc-gender-headword" style={{ color }}>
            {data.article ? `${data.article} ` : ''}{data.word}
            <button className="fc-btn fc-btn-secondary fc-btn-icon" onClick={() => speak(`${data.article} ${data.word}`.trim())}>
              🔊
            </button>
          </div>

          {data.gender && (
            <div className="fc-row fc-gender-pills">
              <span className="fc-pill" style={{ color, background: 'transparent', border: `1px solid ${color}` }}>
                {GENDER_LABELS[data.gender]}
              </span>
              <span className="fc-pill">{data.article} {data.word}</span>
              <span className="fc-pill">{data.indefinite_article} {data.word}</span>
            </div>
          )}

          {data.example && (
            <div className="fc-gender-example">
              <div className="fc-gender-example-fr">
                {data.example}
                <button className="fc-btn fc-btn-secondary fc-btn-icon" onClick={() => speak(data.example)}>🔊</button>
              </div>
              {data.example_translation && <div className="fc-muted">{data.example_translation}</div>}
            </div>
          )}

          {data.pattern_note && <div className="fc-gender-pattern">💡 {data.pattern_note}</div>}
        </div>
      )}
    </div>
  )
}

// ── Translator ───────────────────────────────────────────────────────────────

const DIRECTIONS = [
  { id: 'en_fr', label: 'English → French' },
  { id: 'fr_en', label: 'French → English' },
]

function Translator({ lessonText }) {
  const [text, setText] = useState('')
  const [direction, setDirection] = useState('en_fr')
  const [useContext, setUseContext] = useState(false)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleTranslate = async () => {
    const t = text.trim()
    if (!t) return
    setLoading(true)
    setError('')
    try {
      const result = await translateText(t, direction, useContext ? lessonText : '')
      setData(result)
    } catch (e) {
      setError(`Could not translate: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const switchDirection = (id) => {
    if (id === direction) return
    setDirection(id)
    setData(null)
  }

  return (
    <div>
      <p className="fc-muted">
        Translate a word or phrase between English and French — with alternatives and an example in context.
      </p>

      <div className="fc-row">
        {DIRECTIONS.map((d) => (
          <button
            key={d.id}
            className={`fc-subtab${direction === d.id ? ' fc-subtab-active' : ''}`}
            onClick={() => switchDirection(d.id)}
          >
            {d.label}
          </button>
        ))}
      </div>

      <textarea
        className="fc-textarea"
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={direction === 'en_fr' ? 'Type something in English…' : 'Tapez quelque chose en français…'}
      />

      <div className="fc-row">
        <button className="fc-btn fc-btn-primary" onClick={handleTranslate} disabled={loading || !text.trim()}>
          {loading ? 'Translating…' : '🔁 Translate'}
        </button>
        {direction === 'fr_en' && text.trim() && (
          <button className="fc-btn fc-btn-secondary" onClick={() => speak(text)}>🔊 Hear input</button>
        )}
        {lessonText?.trim() && (
          <label className="fc-checkbox">
            <input type="checkbox" checked={useContext} onChange={(e) => setUseContext(e.target.checked)} />
            Use my current lesson as context
          </label>
        )}
      </div>

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {data && (
        <div className="fc-card fc-translate-result">
          <div className="fc-translate-main">
            {data.translation}
            {direction === 'en_fr' && data.translation && (
              <button className="fc-btn fc-btn-secondary fc-btn-icon" onClick={() => speak(data.translation)}>🔊</button>
            )}
          </div>

          {data.alternatives?.length > 0 && (
            <div className="fc-translate-alts">
              <span className="fc-muted">Also: </span>
              {data.alternatives.join(' · ')}
            </div>
          )}

          {data.example_fr && (
            <div className="fc-translate-example">
              <div>
                {data.example_fr}
                <button className="fc-btn fc-btn-secondary fc-btn-icon" onClick={() => speak(data.example_fr)}>🔊</button>
              </div>
              {data.example_en && <div className="fc-muted">{data.example_en}</div>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

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
      {view === 'translate' && <Translator lessonText={lessonText} />}
      {view === 'text' && <TextChecker />}
    </div>
  )
}
