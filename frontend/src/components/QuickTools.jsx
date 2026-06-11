import { useState } from 'react'
import { genderCheck, translateText } from '../api'
import { speak } from '../tts'

// Shared "quick tools" — the Gender Checker and Translator from the Tools
// screen, also reusable as a side panel while doing exercises (see
// Exercises.jsx).

// ── Gender Checker ───────────────────────────────────────────────────────────

const GENDER_COLORS = { Masc: '#4A90D9', Fem: '#D96B8A' }
const GENDER_LABELS = { Masc: 'Masculine ♂', Fem: 'Feminine ♀' }

export function GenderChecker() {
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

export function TranslatorWidget({ lessonText, onRemove }) {
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
    <div className="fc-card fc-translator-widget">
      {onRemove && (
        <button className="fc-btn fc-btn-secondary fc-btn-icon fc-translator-remove" onClick={onRemove} title="Remove this translator">
          ✕
        </button>
      )}

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
        <div className="fc-translate-result">
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

let widgetIdCounter = 0
function nextWidgetId() {
  widgetIdCounter += 1
  return widgetIdCounter
}

export function TranslatorPanel({ lessonText }) {
  const [widgetIds, setWidgetIds] = useState(() => [nextWidgetId()])

  const addWidget = () => {
    setWidgetIds((ids) => (ids.length < 3 ? [...ids, nextWidgetId()] : ids))
  }

  const removeWidget = (id) => {
    setWidgetIds((ids) => (ids.length > 1 ? ids.filter((i) => i !== id) : ids))
  }

  return (
    <div>
      <p className="fc-muted">
        Translate a word or phrase between English and French — with alternatives and an example in context.
        Add more translators to check a few words or sentences side by side.
      </p>

      <div className="fc-translator-grid">
        {widgetIds.map((id) => (
          <TranslatorWidget
            key={id}
            lessonText={lessonText}
            onRemove={widgetIds.length > 1 ? () => removeWidget(id) : null}
          />
        ))}
      </div>

      {widgetIds.length < 3 && (
        <div className="fc-row" style={{ marginTop: 12 }}>
          <button className="fc-btn" onClick={addWidget}>+ Add another translator</button>
        </div>
      )}
    </div>
  )
}
