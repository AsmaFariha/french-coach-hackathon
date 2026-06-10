import { useEffect, useRef, useState } from 'react'
import {
  generateCoachSet,
  checkCoachExercise,
  startDialogue,
  sendDialogueReply,
  generateVisualExercise,
  getPronunciationTarget,
  checkPronunciation,
} from '../api'
import { speak, speakAll } from '../tts'

const SUBTABS = [
  { id: 'coach', label: '🧠 Coach' },
  { id: 'dialogue', label: '💬 Dialogue' },
  { id: 'visual', label: '📷 Visual' },
  { id: 'pronunciation', label: '🎤 Pronunciation' },
]

// ── Coach Agent exercise set ────────────────────────────────────────────────

const TYPE_LABELS = {
  fill_blank: 'Fill in the blank',
  multiple_choice: 'Multiple choice',
  error_detection: 'Find the change',
  reorder: 'Put it in order',
  translation: 'Translate',
}

function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

// French text worth speaking aloud for this exercise (English prompts for
// "translation" items are deliberately excluded).
function speakableText(exercise) {
  switch (exercise?.type) {
    case 'fill_blank': return exercise.sentence_with_blank
    case 'multiple_choice': return exercise.question
    case 'error_detection': return exercise.sentence
    case 'reorder': return (exercise.words || []).join(' ')
    default: return ''
  }
}

function wordPool(words) {
  return shuffle((words || []).map((word, key) => ({ word, key })))
}

function CoachExercises({ lessonText }) {
  const [data, setData] = useState(null)
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [orderPool, setOrderPool] = useState([])
  const [orderChosen, setOrderChosen] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')

  const exercises = data?.exercises || []
  const total = exercises.length
  const exercise = exercises[index]
  const done = !!data && index >= total

  const resetItem = (ex) => {
    setAnswer('')
    setFeedback(null)
    setOrderPool(ex?.type === 'reorder' ? wordPool(ex.words) : [])
    setOrderChosen([])
  }

  const handleGenerate = async () => {
    setLoading(true)
    setError('')
    setData(null)
    setIndex(0)
    resetItem(null)
    try {
      const result = await generateCoachSet(lessonText)
      setData(result)
      resetItem(result.exercises?.[0])
    } catch (e) {
      setError(`Could not generate exercises: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const currentAnswer = exercise?.type === 'reorder' ? orderChosen.map((c) => c.word).join(' ') : answer

  const handleCheck = async () => {
    if (!exercise || !currentAnswer.trim()) return
    setChecking(true)
    setError('')
    try {
      const result = await checkCoachExercise(exercise, currentAnswer)
      setFeedback(result)
    } catch (e) {
      setError(`Could not check your answer: ${e.message}`)
    } finally {
      setChecking(false)
    }
  }

  const handleNext = () => {
    const next = index + 1
    setIndex(next)
    resetItem(exercises[next])
  }

  const moveToChosen = (item) => {
    setOrderPool((pool) => pool.filter((w) => w.key !== item.key))
    setOrderChosen((chosen) => [...chosen, item])
  }

  const moveToPool = (item) => {
    setOrderChosen((chosen) => chosen.filter((w) => w.key !== item.key))
    setOrderPool((pool) => [...pool, item])
  }

  return (
    <div>
      <p className="fc-muted">
        The Coach Agent plans a mixed practice set from your current lesson, checks each item itself, and walks you through it one at a time.
      </p>
      <div className="fc-row">
        <button className="fc-btn fc-btn-primary" onClick={handleGenerate} disabled={loading}>
          {loading ? 'Planning your practice set…' : data ? '🔄 New practice set' : '✨ Generate practice set'}
        </button>
      </div>

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {data && data.concepts?.length > 0 && (
        <div className="fc-row">
          <span className="fc-muted">This lesson covers:</span>
          {data.concepts.map((c) => (
            <span key={c.id} className="fc-pill">{c.name}</span>
          ))}
        </div>
      )}

      {exercise && (
        <div className="fc-card fc-coach-item">
          <div className="fc-coach-progress">
            <span className="fc-pill">{TYPE_LABELS[exercise.type] || exercise.type}</span>
            <span className="fc-muted">Exercise {index + 1} of {total}</span>
          </div>

          <p className="fc-coach-instruction">{exercise.instruction}</p>

          {exercise.type === 'translation' && (
            <p className="fc-coach-content fc-coach-content-en">{exercise.prompt}</p>
          )}

          {exercise.type !== 'translation' && exercise.type !== 'reorder' && (
            <p className="fc-coach-content">
              {speakableText(exercise)}{' '}
              <button className="fc-chat-speak-btn" onClick={() => speak(speakableText(exercise))}>🔊 Hear it</button>
            </p>
          )}

          {exercise.type === 'fill_blank' && (
            <p className="fc-muted">Hint: {exercise.hint}</p>
          )}

          {exercise.type === 'multiple_choice' && (
            <div className="fc-coach-options">
              {(exercise.options || []).map((opt) => (
                <button
                  key={opt}
                  className={`fc-coach-option${answer === opt ? ' fc-coach-option-selected' : ''}`}
                  onClick={() => !feedback && setAnswer(opt)}
                  disabled={!!feedback}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}

          {exercise.type === 'reorder' && (
            <>
              <button className="fc-chat-speak-btn" onClick={() => speak(speakableText(exercise))}>🔊 Hear the words</button>
              <div className="fc-coach-chips fc-coach-chips-answer">
                {orderChosen.length === 0 && <span className="fc-muted">Tap the words below, in order…</span>}
                {orderChosen.map((item) => (
                  <button
                    key={item.key}
                    className="fc-coach-chip fc-coach-chip-chosen"
                    onClick={() => !feedback && moveToPool(item)}
                    disabled={!!feedback}
                  >
                    {item.word}
                  </button>
                ))}
              </div>
              <div className="fc-coach-chips">
                {orderPool.map((item) => (
                  <button
                    key={item.key}
                    className="fc-coach-chip"
                    onClick={() => !feedback && moveToChosen(item)}
                    disabled={!!feedback}
                  >
                    {item.word}
                  </button>
                ))}
              </div>
            </>
          )}

          {(exercise.type === 'fill_blank' || exercise.type === 'error_detection' || exercise.type === 'translation') && (
            <div className="fc-row" style={{ marginTop: 8 }}>
              <input
                className="fc-input"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Your answer…"
                disabled={!!feedback}
                onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
              />
            </div>
          )}

          {!feedback && (
            <div className="fc-row" style={{ marginTop: 8 }}>
              <button className="fc-btn fc-btn-primary" onClick={handleCheck} disabled={checking || !currentAnswer.trim()}>
                {checking ? 'Checking…' : 'Check answer'}
              </button>
            </div>
          )}

          {feedback && (
            <>
              <div className={`fc-coach-feedback${feedback.correct ? ' fc-coach-feedback-correct' : ''}`}>
                <div className="fc-coach-feedback-title">
                  {feedback.correct ? '✅ Exactly right!' : '💡 Nice try!'}
                </div>
                <div>{feedback.feedback}</div>
                {!feedback.correct && (
                  <div className="fc-coach-feedback-answer">
                    Model answer: <strong>{feedback.answer}</strong>{' '}
                    <button className="fc-chat-speak-btn" onClick={() => speak(feedback.answer)}>🔊</button>
                  </div>
                )}
              </div>
              <div className="fc-row" style={{ marginTop: 8 }}>
                <button className="fc-btn fc-btn-primary" onClick={handleNext}>
                  {index + 1 < total ? 'Next exercise →' : '🎉 Finish set'}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {done && (
        <div className="fc-empty">
          <p>🎉 Practice set complete — great work!</p>
          <button className="fc-btn fc-btn-primary" onClick={handleGenerate}>✨ Generate another set</button>
        </div>
      )}
    </div>
  )
}

// ── Dialogue exercise ─────────────────────────────────────────────────────

// render_dialogue (exercises.py) shows every agent line up front — user
// turns are revealed progressively as replies come in, but the agent's
// side of the script is fixed from the start.
function agentLines(turns) {
  return (turns || []).filter((t) => t.speaker === 'agent').map((t) => t.text)
}

function DialogueExercise({ lessonText }) {
  const [dialogue, setDialogue] = useState(null)
  const [replies, setReplies] = useState([])
  const [transcriptHtml, setTranscriptHtml] = useState('')
  const [hint, setHint] = useState('')
  const [feedbackHtml, setFeedbackHtml] = useState('')
  const [reply, setReply] = useState('')
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const done = dialogue && hint.startsWith('🎉')

  const handleStart = async () => {
    setLoading(true)
    setError('')
    setFeedbackHtml('')
    setReply('')
    try {
      const data = await startDialogue(lessonText)
      setDialogue(data.dialogue)
      setReplies(data.replies)
      setTranscriptHtml(data.transcript_html)
      setHint(data.hint)
      speakAll(agentLines(data.dialogue.turns))
    } catch (e) {
      setError(`Could not start a dialogue: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    if (!reply.trim() || !dialogue) return
    setSending(true)
    setError('')
    try {
      const data = await sendDialogueReply(dialogue, replies, reply)
      setReplies(data.replies)
      setTranscriptHtml(data.transcript_html)
      setHint(data.hint)
      setFeedbackHtml(data.feedback_html)
      setReply('')
    } catch (e) {
      setError(`Could not send your reply: ${e.message}`)
    } finally {
      setSending(false)
    }
  }

  return (
    <div>
      <p className="fc-muted">
        The coach starts a short scene from your current lesson and plays its lines aloud — you reply in French.
      </p>
      <div className="fc-row">
        <button className="fc-btn fc-btn-primary" onClick={handleStart} disabled={loading}>
          {loading ? 'Starting…' : dialogue ? '🔄 New dialogue' : '🎬 Start dialogue'}
        </button>
        {dialogue && (
          <button className="fc-btn" onClick={() => speakAll(agentLines(dialogue.turns))}>
            🔊 Replay
          </button>
        )}
      </div>

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {transcriptHtml && <div dangerouslySetInnerHTML={{ __html: transcriptHtml }} />}

      {dialogue && !done && (
        <div className="fc-row" style={{ marginTop: 12 }}>
          <input
            className="fc-input"
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            placeholder="Type your reply in French…"
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button className="fc-btn" onClick={handleSend} disabled={sending || !reply.trim()}>
            {sending ? 'Sending…' : 'Send reply'}
          </button>
        </div>
      )}

      {hint && <div className="fc-status">{hint}</div>}

      {feedbackHtml && <div dangerouslySetInnerHTML={{ __html: feedbackHtml }} />}
    </div>
  )
}

// ── Visual exercise ───────────────────────────────────────────────────────

function VisualExercise() {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [html, setHtml] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setFile(f)
    setPreviewUrl(URL.createObjectURL(f))
    setHtml('')
    setError('')
  }

  const handleGenerate = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const data = await generateVisualExercise(file)
      setHtml(data.html)
    } catch (e) {
      setError(`Could not generate exercises from this photo: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="fc-muted">
        Snap a photo of a menu, sign, or recipe — the coach reads it and builds exercises from what's in the picture.
      </p>
      <div className="fc-row">
        <input className="fc-input" type="file" accept="image/*" onChange={handleFileChange} />
        <button className="fc-btn fc-btn-primary" onClick={handleGenerate} disabled={!file || loading}>
          {loading ? 'Reading photo…' : '✨ Generate exercises'}
        </button>
      </div>

      {previewUrl && (
        <div className="fc-row">
          <img className="fc-visual-preview" src={previewUrl} alt="Selected" />
        </div>
      )}

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {html && <div dangerouslySetInnerHTML={{ __html: html }} />}
    </div>
  )
}

// ── Pronunciation exercise ────────────────────────────────────────────────

function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function PronunciationExercise({ lessonText }) {
  const [target, setTarget] = useState(null)
  const [html, setHtml] = useState('')
  const [transcription, setTranscription] = useState('')
  const [feedbackHtml, setFeedbackHtml] = useState('')
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(false)
  const [listening, setListening] = useState(false)
  const [error, setError] = useState('')
  const recognitionRef = useRef(null)

  const speechSupported = !!getSpeechRecognition()

  const handleGetPhrase = async () => {
    setLoading(true)
    setError('')
    setFeedbackHtml('')
    setTranscription('')
    try {
      const data = await getPronunciationTarget(lessonText)
      setTarget(data.target)
      setHtml(data.html)
      speak(data.target.phrase)
    } catch (e) {
      setError(`Could not get a phrase: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleMic = () => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) return
    const recognition = new SpeechRecognition()
    recognition.lang = 'fr-FR'
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    recognitionRef.current = recognition

    recognition.onresult = (e) => {
      setTranscription(e.results[0][0].transcript)
    }
    recognition.onerror = () => {
      setError('Could not hear you — check microphone permissions and try again.')
      setListening(false)
    }
    recognition.onend = () => setListening(false)

    setError('')
    setListening(true)
    recognition.start()
  }

  const handleCheck = async () => {
    if (!target || !transcription.trim()) return
    setChecking(true)
    setError('')
    try {
      const data = await checkPronunciation(target, transcription)
      setFeedbackHtml(data.html)
    } catch (e) {
      setError(`Could not check pronunciation: ${e.message}`)
    } finally {
      setChecking(false)
    }
  }

  return (
    <div>
      <p className="fc-muted">
        The coach speaks a phrase from your lesson aloud — repeat it, and get gentle feedback on your pronunciation.
      </p>
      <div className="fc-row">
        <button className="fc-btn fc-btn-primary" onClick={handleGetPhrase} disabled={loading}>
          {loading ? 'Thinking…' : target ? '🔄 New phrase' : '🎯 Get a phrase'}
        </button>
        {target && (
          <button className="fc-btn" onClick={() => speak(target.phrase)}>🔊 Hear it again</button>
        )}
      </div>

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {html && <div dangerouslySetInnerHTML={{ __html: html }} />}

      {target && (
        <>
          <div className="fc-row" style={{ marginTop: 12 }}>
            <input
              className="fc-input"
              value={transcription}
              onChange={(e) => setTranscription(e.target.value)}
              placeholder="What you said (or type it yourself)…"
              onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
            />
            {speechSupported && (
              <button className={`fc-btn fc-mic-btn${listening ? ' fc-mic-listening' : ''}`} onClick={handleMic}>
                {listening ? '🎙️ Listening…' : '🎤 Use microphone'}
              </button>
            )}
            <button className="fc-btn" onClick={handleCheck} disabled={checking || !transcription.trim()}>
              {checking ? 'Checking…' : 'Check pronunciation'}
            </button>
          </div>
          {!speechSupported && (
            <p className="fc-muted">
              Your browser doesn't support speech input — type what you said instead.
            </p>
          )}
          {feedbackHtml && <div dangerouslySetInnerHTML={{ __html: feedbackHtml }} />}
        </>
      )}
    </div>
  )
}

// ── Screen ─────────────────────────────────────────────────────────────────

export default function Exercises({ lessonText }) {
  const [view, setView] = useState('coach')

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

      {view === 'coach' && <CoachExercises lessonText={lessonText} />}
      {view === 'dialogue' && <DialogueExercise lessonText={lessonText} />}
      {view === 'visual' && <VisualExercise />}
      {view === 'pronunciation' && <PronunciationExercise lessonText={lessonText} />}
    </div>
  )
}
